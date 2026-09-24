import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { currentUserQueryKey } from '@/features/auth/api'
import { apiGet, apiPatch, apiPost } from '@/lib/api'
import type {
  CreateUserRequest,
  Paginated,
  UpdateUserRequest,
  User,
  UserListParams,
} from '@/types/api'

export const usersQueryKey = ['admin', 'users'] as const

/** Drop empty filters so they are not sent as `?role=&search=`. */
function cleanParams(params: UserListParams): UserListParams {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  ) as UserListParams
}

export function useUsers(params: UserListParams) {
  const cleaned = cleanParams(params)
  return useQuery({
    queryKey: [...usersQueryKey, cleaned],
    queryFn: () => apiGet<Paginated<User>>('/admin/users', cleaned),
    placeholderData: keepPreviousData,
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateUserRequest) => apiPost<User>('/admin/users', input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersQueryKey }),
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, changes }: { id: number; changes: UpdateUserRequest }) =>
      apiPatch<User>(`/admin/users/${id}`, changes),
    onSuccess: (updated) => {
      // If admins edit their own record, keep the top bar and profile in sync.
      queryClient.setQueryData<User | null>(currentUserQueryKey, (current) =>
        current && current.id === updated.id ? updated : current,
      )
      return queryClient.invalidateQueries({ queryKey: usersQueryKey })
    },
  })
}
