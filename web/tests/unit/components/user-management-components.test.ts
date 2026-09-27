import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog'
import { CreateTokenDialog } from '@/components/create-token-dialog'
import { UserDialog } from '@/components/user-dialog'
import { UserTable } from '@/components/user-table'

describe('user management components', () => {
  it('renders the permanent token-revocation warning with the user identity', () => {
    const markup = renderToStaticMarkup(
      React.createElement(ConfirmDeleteDialog, {
        isOpen: true,
        title: 'Delete user',
        description:
          'Deleting Ada Lovelace will permanently revoke all tokens owned by this user.',
        targetKey: 'Ada Lovelace',
        onConfirm: () => undefined,
        onClose: () => undefined,
      })
    )

    expect(markup).toContain('permanently revoke all tokens owned by this user')
    expect(markup).toContain('Ada Lovelace')
  })

  it('limits user create and edit forms to name and email', () => {
    const markup = renderToStaticMarkup(
      React.createElement(UserDialog, {
        isOpen: true,
        onClose: () => undefined,
        onSuccess: () => undefined,
      })
    )

    expect(markup).toContain('Name')
    expect(markup).toContain('Email')
    expect(markup).not.toContain('tenant_id')
    expect(markup).not.toContain('Tenant')
  })

  it('renders exact row actions for each user', () => {
    const markup = renderToStaticMarkup(
      React.createElement(UserTable, {
        users: [{ id: 'user-1', name: 'Ada', email: 'ada@example.com' }],
        onRefresh: () => undefined,
        search: '',
        onSearchChange: () => undefined,
        page: 0,
        onPageChange: () => undefined,
        hasMore: false,
        onCreateToken: () => undefined,
      })
    )

    expect(markup).toContain('Edit user')
    expect(markup).toContain('Delete user')
    expect(markup).toContain('Create token for Ada')
  })

  it('locks user token ownership and hides non-expiring lifetime', () => {
    const markup = renderToStaticMarkup(
      React.createElement(CreateTokenDialog, {
        isOpen: true,
        onClose: () => undefined,
        onSuccess: () => undefined,
        userOwner: { kind: 'user', id: 'user-1', name: 'Ada Lovelace' },
      })
    )

    expect(markup).toContain('Owner (User):')
    expect(markup).toContain('Ada Lovelace')
    expect(markup).toContain('30 Days')
    expect(markup).toContain('90 Days')
    expect(markup).not.toContain('Never Expires')
    expect(markup).not.toContain('Owner (Service Account):')
  })

  it('offers tenant selection for user token project grants', () => {
    const markup = renderToStaticMarkup(
      React.createElement(CreateTokenDialog, {
        isOpen: true,
        onClose: () => undefined,
        onSuccess: () => undefined,
        userOwner: { kind: 'user', id: 'user-1', name: 'Ada' },
        tenants: [{ id: 'tenant-1', name: 'Platform', status: 'active' }],
      })
    )

    expect(markup).toContain('All projects (all tenants)')
    expect(markup).toContain('Platform')
    expect(markup).not.toContain("Projects in this user's tenant")
  })
})
