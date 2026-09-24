import { z } from 'zod'

const MIN_LENGTH = 8
const MAX_BYTES = 72 // bcrypt limit, enforced by the API as well

/** A new password, matching the server rules (8+ characters, at most 72 bytes). */
export const newPasswordSchema = z
  .string()
  .min(MIN_LENGTH, `Password must be at least ${MIN_LENGTH} characters.`)
  .refine(
    (value) => new TextEncoder().encode(value).length <= MAX_BYTES,
    `Password must be at most ${MAX_BYTES} bytes.`,
  )

/** New password + confirmation, for forms that ask for both. */
export const passwordWithConfirmSchema = z
  .object({ new_password: newPasswordSchema, confirm_password: z.string() })
  .refine((values) => values.new_password === values.confirm_password, {
    message: 'Passwords do not match.',
    path: ['confirm_password'],
  })
