import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const ADMIN_TOKEN = process.env.API_ADMIN_TOKEN || 'test-admin-secret-e2e'

test('Full UI Walkthrough Video Recording', async ({ page }) => {
  // 1. Visit root -> redirected to /login
  await page.goto('/')
  await expect(page).toHaveURL(/\/login/)
  await page.waitForTimeout(1200)

  // 2. Type admin token in input
  const tokenInput = page.locator('input[name="token"]')
  await tokenInput.pressSequentially(ADMIN_TOKEN, { delay: 40 })
  await page.waitForTimeout(800)

  // 3. Click Login button
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL('/')
  await page.waitForTimeout(2000)

  // 4. Open "New Token" modal
  await page.click('button:has-text("New Token")')
  await page.waitForTimeout(1000)

  // 5. Fill token form
  const nameInput = page.locator('input[placeholder*="github-actions"]')
  await nameInput.pressSequentially('ci-production-pipeline', { delay: 45 })
  await page.waitForTimeout(800)

  // Toggle memory:publish
  const publishCheckbox = page.locator('label:has-text("memory:publish") input[type="checkbox"]')
  if (!(await publishCheckbox.isChecked())) {
    await publishCheckbox.check()
    await page.waitForTimeout(600)
  }

  // Select 30 days lifetime
  await page.click('button:has-text("30 Days")')
  await page.waitForTimeout(1000)

  // 6. Submit token creation
  await page.click('button:has-text("Create Token")')

  // 7. Verify One-Time Reveal Modal
  await expect(page.locator('text=Token Issued Successfully!')).toBeVisible()
  await expect(page.locator('text=One-Time Reveal Notice')).toBeVisible()
  await page.waitForTimeout(2500)

  // 8. Copy secret
  await page.click('button:has-text("Copy")')
  await expect(page.locator('text=Copied!')).toBeVisible()
  await page.waitForTimeout(1500)

  // 9. Close modal
  await page.click('button:has-text("Done and Close")')
  await expect(page.locator('text=Token Issued Successfully!')).not.toBeVisible()
  await page.waitForTimeout(2000)

  // 10. Locate newly created token in table and revoke it
  const newRow = page.locator('tr:has-text("ci-production-pipeline")')
  await expect(newRow).toBeVisible()
  await page.waitForTimeout(1000)

  await newRow.locator('button[title="Revoke token"]').click()
  await expect(newRow.locator('button:has-text("Confirm")')).toBeVisible()
  await page.waitForTimeout(1000)

  await newRow.locator('button:has-text("Confirm")').click()
  await expect(page.locator('tr:has-text("ci-production-pipeline")')).not.toBeVisible()
  await page.waitForTimeout(2000)

  // 11. Logout
  await page.click('button:has-text("Sign Out")')
  await expect(page).toHaveURL(/\/login/)
  await page.waitForTimeout(1500)

  // 12. Save recorded video to docs/assets/harness-memory-admin-demo.webm
  const video = page.video()
  if (video) {
    const targetDir = 'c:/Users/corre/Documents/harness-memory/docs/assets'
    if (!fs.existsSync(targetDir)) {
      fs.mkdirSync(targetDir, { recursive: true })
    }
    const targetFile = path.join(targetDir, 'harness-memory-admin-demo.webm')
    await page.close()
    await video.saveAs(targetFile)
    console.log(`[VIDEO EXPORTED] -> ${targetFile}`)
  }
})
