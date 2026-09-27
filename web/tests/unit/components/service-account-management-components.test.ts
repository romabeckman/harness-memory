import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog'
import { CreateTokenDialog } from '@/components/create-token-dialog'
import {
  getInitialServiceAccountTenantId,
  ServiceAccountDialog,
} from '@/components/service-account-dialog'
import { ServiceAccountTable } from '@/components/service-account-table'

const account = {
  id: 'sa-1',
  tenant_id: 'tenant-1',
  name: 'Release bot',
}

const organization = {
  id: 'tenant-1',
  name: 'Platform',
  status: 'active' as const,
}

describe('service-account management components', () => {
  it('renders global rows with organization context and row actions', () => {
    const markup = renderToStaticMarkup(
      React.createElement(ServiceAccountTable, {
        accounts: [account],
        organizations: [organization],
        hasMore: false,
        loading: false,
        onCreateToken: () => undefined,
        onDelete: () => undefined,
        onEdit: () => undefined,
        onPageChange: () => undefined,
        page: 0,
        onRefresh: () => undefined,
        onSearchChange: () => undefined,
        search: '',
      })
    )

    expect(markup).toContain('Release bot')
    expect(markup).toContain('Platform')
    expect(markup).toContain('Create token for Release bot')
    expect(markup).toContain('Edit service account Release bot')
    expect(markup).toContain('Delete service account Release bot')
  })

  it('requires organization on create and keeps organization read-only on edit', () => {
    const createMarkup = renderToStaticMarkup(
      React.createElement(ServiceAccountDialog, {
        isOpen: true,
        onClose: () => undefined,
        onSuccess: () => undefined,
        organizations: [organization],
      })
    )
    const editMarkup = renderToStaticMarkup(
      React.createElement(ServiceAccountDialog, {
        account,
        isOpen: true,
        onClose: () => undefined,
        onSuccess: () => undefined,
        organizations: [organization],
      })
    )

    expect(createMarkup).toContain('Organization')
    expect(createMarkup).toContain('required')
    expect(editMarkup).toContain('Organization: Platform')
    expect(editMarkup).not.toContain('name="tenant_id"')
  })

  it('does not choose an organization before the administrator selects one', () => {
    expect(
      getInitialServiceAccountTenantId(undefined, [organization])
    ).toBe('')
  })

  it('states permanent owned-token revocation before destructive confirmation', () => {
    const markup = renderToStaticMarkup(
      React.createElement(ConfirmDeleteDialog, {
        isOpen: true,
        title: 'Delete service account',
        description:
          'Deleting Release bot will permanently revoke all tokens owned by this service account.',
        targetKey: 'Release bot',
        onConfirm: () => undefined,
        onClose: () => undefined,
      })
    )

    expect(markup).toContain('permanently revoke all tokens owned by this service account')
    expect(markup).toContain('Release bot')
  })

  it('renders the selected service-account owner as visible and locked', () => {
    const markup = renderToStaticMarkup(
      React.createElement(CreateTokenDialog, {
        isOpen: true,
        onClose: () => undefined,
        onSuccess: () => undefined,
        serviceAccountOwner: {
          kind: 'service-account',
          id: 'sa-1',
          name: 'Release bot',
          tenantId: 'tenant-1',
          tenantName: 'Platform',
        },
      })
    )

    expect(markup).toContain('Owner (Service Account):')
    expect(markup).toContain('Release bot')
    expect(markup).toContain('Platform')
    expect(markup).toContain('30 Days')
    expect(markup).toContain('90 Days')
    expect(markup).toContain('Never Expires')
  })
})
