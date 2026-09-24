import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, apiGet, apiPost } from '@/lib/api'
import type { ChangePasswordRequest, LoginRequest, LoginResponse, User } from '@/types/api'

export const currentUserQueryKey = ['auth', 'me'] as const

/** The logged-in user, or null when there is no valid session. */
export async function fetchCurrentUser(): Promise<User | null> {
  try {
    return await apiGet<User>('/auth/me')
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60_000,
    retry: false,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: LoginRequest) => apiPost<LoginResponse>('/auth/login', input),
    onSuccess: ({ user }) => {
      // Drop anything cached for a previous user before storing the new one.
      queryClient.removeQueries()
      queryClient.setQueryData(currentUserQueryKey, user)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => apiPost<unknown>('/auth/logout'),
    onSettled: () => {
      queryClient.removeQueries()
      queryClient.setQueryData(currentUserQueryKey, null)
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (input: ChangePasswordRequest) =>
      apiPost<{ message: string }>('/auth/change-password', input),
  })
}
