import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProjectAdminsSection from './ProjectAdminsSection'

const h = vi.hoisted(() => ({ grant: vi.fn(), revoke: vi.fn() }))
vi.mock('./api', () => ({
  useProjectAdmins: () => ({
    isLoading: false,
    isError: false,
    data: [
      { user_id: 'coach', first_name: 'Coach', last_name: 'One', email: 'coach@example.com', granted_at: '' },
    ],
  }),
  useRevokeProjectAdmin: () => ({ mutate: h.revoke, isPending: false, isError: false, variables: undefined }),
  useGrantProjectAdmin: () => ({ mutate: h.grant, isPending: false, isError: false }),
  useAdminUsers: () => ({
    isLoading: false,
    isError: false,
    data: {
      users: [
        { id: 'coach', first_name: 'Coach', last_name: 'One', email: 'coach@example.com', role: 'user', project_name: 'P' },
        { id: 'power', first_name: 'Power', last_name: 'Admin', email: 'power@example.com', role: 'admin', project_name: null },
        { id: 'new', first_name: 'New', last_name: 'Lead', email: 'lead@example.com', role: 'user', project_name: null },
      ],
    },
  }),
}))

beforeEach(() => {
  h.grant.mockReset()
  h.revoke.mockReset()
})

describe('ProjectAdminsSection', () => {
  it('is read-only for a project admin', () => {
    render(<ProjectAdminsSection projectId="p1" canEdit={false} />)
    expect(screen.getByText('coach@example.com')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add admin' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument()
  })

  it('lets a power admin add someone who is not yet an admin', async () => {
    render(<ProjectAdminsSection projectId="p1" canEdit />)
    fireEvent.click(screen.getByRole('button', { name: 'Add admin' }))
    fireEvent.change(screen.getByLabelText('Find a person by name or email'), { target: { value: 'le' } })
    // Existing admins and power admins are not offered.
    expect(await screen.findAllByRole('button', { name: 'Make admin' })).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Make admin' }))
    expect(h.grant).toHaveBeenCalledWith({ projectId: 'p1', userId: 'new' }, expect.anything())
  })

  it('lets a power admin remove an admin after confirming', () => {
    render(<ProjectAdminsSection projectId="p1" canEdit />)
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(h.revoke).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm remove' }))
    expect(h.revoke).toHaveBeenCalledWith({ projectId: 'p1', userId: 'coach' })
  })
})
