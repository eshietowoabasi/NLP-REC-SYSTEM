import { expect, test } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// Full planner workflow from spec §6 / §22 ("login through report").
// Needs users admin / planner / viewer (password in E2E_PASSWORD) and an empty database.
const here = path.dirname(fileURLToPath(import.meta.url))
const fixture = (name) => path.join(here, 'fixtures', name)
const PASSWORD = process.env.E2E_PASSWORD || 'Passw0rd!'
const shots = process.env.E2E_SCREENSHOTS

async function login(page, username) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByTestId('current-user')).toContainText(username)
}

async function logout(page) {
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/login/)
}

async function upload(page, file, category) {
  await page.getByLabel('File (PDF, DOCX or TXT, max 25 MB)').setInputFiles(fixture(file))
  await page.getByLabel('Source category').selectOption(category)
  await page.getByRole('button', { name: 'Upload', exact: true }).click()
  await expect(page.getByTestId('upload-notice')).toContainText('Uploaded')
}

async function snap(page, name) {
  if (shots) await page.screenshot({ path: path.join(shots, `${name}.png`), fullPage: true })
}

test.describe.configure({ mode: 'serial' })

test('unauthenticated users are sent to login', async ({ page }) => {
  await page.goto('/sessions')
  await expect(page).toHaveURL(/\/login\?next=\/sessions$/)
  await page.getByLabel('Username').fill('planner')
  await page.getByLabel('Password').fill('wrong')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('alert')).toContainText('Invalid username or password')
})

test('admin uploads the NUC core reference', async ({ page }) => {
  await login(page, 'admin')
  await expect(page.getByTestId('core-warning')).toBeVisible()
  await page.getByRole('link', { name: 'Documents' }).click()
  await upload(page, 'ccmas-core-sample.txt', 'NUC Core Reference')
  await logout(page)
})

test('planner runs an analysis, reviews, maps and reports', async ({ page }) => {
  await login(page, 'planner')
  await page.getByRole('link', { name: 'Documents' }).click()
  // Planners cannot upload core references.
  await expect(page.getByLabel('Source category').locator('option', { hasText: 'NUC Core Reference' })).toHaveCount(0)
  for (const theme of ['cloud', 'security', 'data']) await upload(page, `${theme}-job-adverts.txt`, 'Job Market Data')
  await expect(page.getByTestId('documents-table').locator('tbody tr')).toHaveCount(4)
  await snap(page, '01-documents')

  await page.getByRole('link', { name: 'Sessions', exact: true }).click()
  await page.getByLabel('Session name').fill('E2E Computing Review')
  for (const theme of ['cloud', 'security', 'data']) await page.getByLabel(new RegExp(`^${theme}-job-adverts`)).check()
  await page.getByRole('button', { name: 'Create session' }).click()
  await expect(page).toHaveURL(/\/sessions\/\d+$/)
  await expect(page.getByTestId('session-status')).toHaveText('Pending')

  await page.getByTestId('run').click()
  await expect(page.getByTestId('session-status')).toHaveText('Completed', { timeout: 90_000 })
  await snap(page, '02-session-completed')

  await page.getByTestId('view-recommendations').click()
  const cards = page.locator('[data-test^="rec-"]').filter({ has: page.getByTestId('rec-title') })
  await expect(cards.first()).toBeVisible()
  expect(await cards.count()).toBeGreaterThan(2)
  await snap(page, '03-recommendations')

  // Accepting a potential duplicate without notes is refused.
  const duplicate = cards.filter({ hasText: 'Potential Duplicate' }).first()
  await duplicate.getByTestId('accept').click()
  await expect(page.getByRole('alert')).toContainText('requires planner notes')
  await duplicate.getByTestId('reject').click()
  await expect(duplicate.getByTestId('decision-badge')).toHaveText('Rejected')

  const novel = cards.filter({ hasText: 'No Significant Overlap' }).first()
  await novel.getByLabel('Planner notes').fill('Strong regional demand for cloud skills.')
  await novel.getByTestId('accept').click()
  await expect(novel.getByTestId('decision-badge')).toHaveText('Accepted')
  await expect(page.getByTestId('decision-counts')).toContainText('1 accepted · 1 rejected')

  await novel.getByTestId('rec-title').click()
  await expect(page.getByTestId('rec-heading')).toBeVisible()
  await snap(page, '04-recommendation-detail')
  await page.getByTestId('map-link').click()
  await page.getByLabel('Course code').fill('csc413')
  await page.getByLabel('Course title').fill('Cloud Infrastructure and DevOps')
  await page.getByLabel('Credit units').selectOption('3')
  await page.getByLabel('Prerequisites (comma-separated codes)').fill('CSC 201')
  await page.getByLabel('Learning outcome 1').fill('Deploy containerised services on a public cloud')
  await page.getByRole('button', { name: 'Add outcome' }).click()
  await page.getByLabel('Learning outcome 2').fill('Automate infrastructure with Terraform')
  await page.getByRole('button', { name: 'Add course' }).click()
  await expect(page.getByTestId('mapping-saved')).toHaveText('Saved CSC 413.')
  await snap(page, '05-mapping')

  // Evidence dashboard tabs.
  await page.getByRole('link', { name: 'Sessions', exact: true }).click()
  await page.getByRole('link', { name: 'E2E Computing Review' }).click()
  await page.getByRole('link', { name: 'Evidence dashboard' }).click()
  await expect(page.getByText('Kubernetes').first()).toBeVisible()
  await page.getByTestId('tab-topics').click()
  await expect(page.getByText(/themes from \d+ passages/)).toBeVisible()
  await page.getByTestId('tab-similarity').click()
  await expect(page.getByText('Potential Duplicate').first()).toBeVisible()
  await snap(page, '06-evidence-similarity')
  await page.getByRole('navigation').getByRole('link', { name: 'Session', exact: true }).click()

  const [download] = await Promise.all([page.waitForEvent('download'), page.getByTestId('report-pdf').click()])
  expect(download.suggestedFilename()).toMatch(/^NLP-RS_E2E_Computing_Review_.*\.pdf$/)
  await page.getByRole('link', { name: 'Reports' }).click()
  await expect(page.getByTestId('reports-table').locator('tbody tr')).toHaveCount(1)
  await logout(page)
})

test('viewer has read-only access', async ({ page }) => {
  await login(page, 'viewer')
  await page.getByRole('link', { name: 'Documents' }).click()
  await expect(page.getByTestId('upload-form')).toHaveCount(0)
  await page.getByRole('link', { name: 'Sessions', exact: true }).click()
  await expect(page.getByTestId('session-form')).toHaveCount(0)
  await page.getByRole('link', { name: 'E2E Computing Review' }).click()
  await expect(page.getByTestId('run')).toHaveCount(0)
  await page.getByTestId('view-recommendations').click()
  await expect(page.getByTestId('accept')).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Users' })).toHaveCount(0)
  await page.goto('/admin/users')
  await expect(page).toHaveURL(/\/dashboard/)
  await logout(page)
})

test('admin manages users and reviews the audit log', async ({ page }) => {
  await login(page, 'admin')
  await page.getByRole('link', { name: 'Users' }).click()
  await page.getByLabel('Username').fill('newplanner')
  await page.getByLabel('Email').fill('newplanner@uniuyo.edu.ng')
  await page.getByLabel('Password').fill('Another-pass1')
  await page.getByRole('button', { name: 'Add user' }).click()
  await expect(page.getByText('Created newplanner.')).toBeVisible()
  await page.getByRole('link', { name: 'Audit log' }).click()
  await expect(page.getByText('RECOMMENDATION_DECISION').first()).toBeVisible()
  await expect(page.getByText('MAPPING_CREATE').first()).toBeVisible()
  await snap(page, '07-audit-log')
})
