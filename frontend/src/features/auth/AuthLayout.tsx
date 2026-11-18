import type { ReactNode } from 'react'

const STEPS = ['1 · Review', '2 · Design courses', '3 · Report']

/** Sign-in and sign-up (Login.dc.html): the form on the left, the photo with a caption on the right. */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-svh gap-7 bg-sand p-4 sm:p-7">
      <div className="flex w-full flex-col justify-between gap-10 rounded-[28px] border-[1.5px] border-[#e8c9b6] bg-white px-6 py-8 sm:px-12 sm:py-12 lg:w-[620px] lg:shrink-0 lg:px-[72px]">
        {children}
      </div>

      <div className="relative hidden flex-1 overflow-hidden rounded-[28px] bg-[#e9d8c8] lg:block">
        <img
          src="/assets/login-photo.jpg"
          alt="Two students reading a book together in a library"
          className="absolute inset-0 size-full object-cover"
        />
        <div className="absolute inset-x-7 bottom-7 flex flex-col gap-3.5 rounded-[22px] bg-ink/85 px-7 py-[26px] text-white">
          <p className="text-[26px] leading-tight font-extrabold tracking-[-0.02em]">
            Design the courses the job market is asking for.
          </p>
          <ul className="flex flex-wrap gap-2.5" aria-label="How it works">
            {STEPS.map((step) => (
              <li
                key={step}
                className="rounded-full bg-white/15 px-3 py-[7px] text-[13px] font-semibold"
              >
                {step}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </main>
  )
}
