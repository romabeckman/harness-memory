'use server'

import { revalidatePath } from 'next/cache'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import {
  CreateUserDto,
  UpdateUserDto,
  UserDto,
} from '@/application/ports/harness-api-client.port'

type ListUsersResult = { data?: UserDto[]; error?: string }
type UserMutationResult = { success: boolean; data?: UserDto; error?: string }

export async function listUsersAction(
  query?: string,
  limit?: number,
  offset?: number
): Promise<ListUsersResult> {
  try {
    const data = await ClientFactory.getHarnessClient().listUsers(query, limit, offset)
    return { data }
  } catch (error: unknown) {
    return { error: toSafeError(error, 'Failed to load users') }
  }
}

export async function createUserAction(payload: CreateUserDto): Promise<UserMutationResult> {
  if (!payload.name?.trim()) return { success: false, error: 'User name is required' }
  if (!payload.email?.trim()) return { success: false, error: 'User email is required' }

  try {
    const data = await ClientFactory.getHarnessClient().createUser({
      name: payload.name.trim(),
      email: payload.email.trim(),
    })
    revalidatePath('/users')
    return { success: true, data }
  } catch (error: unknown) {
    return { success: false, error: toSafeError(error, 'Failed to create user') }
  }
}

export async function updateUserAction(
  userId: string,
  payload: UpdateUserDto
): Promise<UserMutationResult> {
  if (!userId.trim()) return { success: false, error: 'User ID is required' }
  if (payload.name !== undefined && !payload.name.trim()) {
    return { success: false, error: 'User name is required' }
  }
  if (payload.email !== undefined && !payload.email.trim()) {
    return { success: false, error: 'User email is required' }
  }

  try {
    const data = await ClientFactory.getHarnessClient().updateUser(userId, {
      ...(payload.name !== undefined ? { name: payload.name.trim() } : {}),
      ...(payload.email !== undefined ? { email: payload.email.trim() } : {}),
    })
    revalidatePath('/users')
    return { success: true, data }
  } catch (error: unknown) {
    return { success: false, error: toSafeError(error, 'Failed to update user') }
  }
}

export async function deleteUserAction(userId: string): Promise<{ success: boolean; error?: string }> {
  if (!userId.trim()) return { success: false, error: 'User ID is required' }

  try {
    await ClientFactory.getHarnessClient().deleteUser(userId)
    revalidatePath('/users')
    return { success: true }
  } catch (error: unknown) {
    return { success: false, error: toSafeError(error, 'Failed to delete user') }
  }
}

function toSafeError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}
