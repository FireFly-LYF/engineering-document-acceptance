import { rpcError, type SessionIdParams } from '@agnes/protocol'
import type { SessionPreferencesStore } from '../../storage/session-preferences.js'
import type { SessionPrincipalOwnership } from '../../storage/session-ownership.js'
import type { SessionWorkspacePort } from '../../storage/lister.js'
import type { CallContext, LocalEndpoint } from '../endpoint.js'
import type { SessionLister } from '../ports.js'

export type SessionDeleteDeps = {
  lister: SessionLister
  preferences: SessionPreferencesStore
  workspaces: SessionWorkspacePort
  /** Drop workspace_bindings + used-session bookkeeping when present. */
  forgetBinding?(sessionId: string): void
  ownership?: SessionPrincipalOwnership
  /** Close a live registry entry when the session is still open. */
  close(sessionId: string): Promise<void>
  /** Purge core ledger rows in sessions.db (events / registers / claims / sessions). */
  purgeLedger?(sessionId: string): Promise<void>
}

/**
 * Permanently delete a local session: close it, drop listing/ownership indexes, and purge the
 * durable ledger when a purge port is available. Local owner auth matches rename/archive.
 */
export function registerSessionDelete(endpoint: LocalEndpoint, deps: SessionDeleteDeps): void {
  const requireSession = async (sessionId: string, context: CallContext) => {
    if (context.conn.authKind !== 'local' || context.conn.credentialKind !== 'local')
      throw rpcError('CAPABILITY_DENIED', { reason: 'local owner required' })
    let cursor: string | undefined
    do {
      const page = await deps.lister.list({ q: sessionId, limit: 500, ...(cursor ? { cursor } : {}) })
      if (page.items.some((row) => row.sessionId === sessionId)) return
      if (page.cursor === cursor) break
      cursor = page.cursor
    } while (cursor !== undefined)
    throw rpcError('SESSION_NOT_FOUND', { sessionId })
  }

  endpoint.register('_agnes/v1/session.delete', async (params, context) => {
    const request = params as SessionIdParams
    const sessionId = request.sessionId
    await requireSession(sessionId, context)

    if (deps.ownership) {
      const owner = deps.ownership.resolve(sessionId)
      if (!owner || owner.principalId !== context.conn.principalId)
        throw rpcError('SESSION_NOT_FOUND', { sessionId })
    }

    await deps.close(sessionId).catch(() => undefined)
    deps.workspaces.remove(sessionId)
    deps.forgetBinding?.(sessionId)
    deps.preferences.remove(sessionId)
    if (deps.ownership && !deps.ownership.release(sessionId, context.conn.principalId))
      throw rpcError('SESSION_NOT_FOUND', { sessionId })
    if (deps.purgeLedger) await deps.purgeLedger(sessionId)
    return {}
  })
}
