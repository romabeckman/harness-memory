import { test, expect } from '@playwright/test'

const ADMIN_TOKEN = process.env.API_ADMIN_TOKEN || 'test-admin-secret-e2e'

test.describe('Harness Memory Admin Console — Tenants & Projects E2E Suite', () => {
  // Helper to authenticate
  const login = async (page: any) => {
    await page.goto('/login')
    await page.fill('input[name="token"]', ADMIN_TOKEN)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')
  }

  test('SCN-E2E-NAV-01: should redirect unauthenticated requests from /tenants and /projects to /login', async ({
    page,
  }) => {
    // 1. Visit /tenants directly unauthenticated
    await page.goto('/tenants')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('h1')).toContainText('Harness Memory')

    // 2. Visit /projects directly unauthenticated
    await page.goto('/projects')
    await expect(page).toHaveURL(/\/login/)
  })

  test('SCN-E2E-NAV-02: should navigate seamlessly via AdminSidebar with active states and collapse toggle', async ({
    page,
  }) => {
    await login(page)

    // Sidebar should be visible on /
    const sidebar = page.locator('aside')
    await expect(sidebar).toBeVisible()

    // 1. Navigate to Tenants
    await page.click('aside a[href="/tenants"]')
    await expect(page).toHaveURL('/tenants')
    await expect(page.locator('h1')).toContainText('Organizações (Tenants)')
    await expect(page.locator('aside a[href="/tenants"]')).toHaveClass(/text-blue-400/)

    // 2. Navigate to Projects
    await page.click('aside a[href="/projects"]')
    await expect(page).toHaveURL('/projects')
    await expect(page.locator('h1')).toContainText('Projetos de Software')
    await expect(page.locator('aside a[href="/projects"]')).toHaveClass(/text-blue-400/)

    // 3. Return to Tokens (Dashboard)
    await page.click('aside a[href="/"]')
    await expect(page).toHaveURL('/')
    await expect(page.locator('h1')).toContainText('Tokens de Acesso & Credenciais')
    await expect(page.locator('aside a[href="/"]')).toHaveClass(/text-blue-400/)

    // 4. Test sidebar collapse/expand toggle
    const toggleButton = page.locator('aside button[title="Recolher menu"]')
    if (await toggleButton.isVisible()) {
      await toggleButton.click()
      await expect(page.locator('aside button[title="Expandir menu"]')).toBeVisible()
      // Expand back
      await page.click('aside button[title="Expandir menu"]')
      await expect(page.locator('aside button[title="Recolher menu"]')).toBeVisible()
    }
  })

  test('SCN-E2E-TENANT-01: should create, search, and edit a Tenant', async ({ page }) => {
    await login(page)
    await page.click('aside a[href="/tenants"]')
    await expect(page).toHaveURL('/tenants')

    // 1. Open "Novo Tenant" Dialog
    await page.click('button:has-text("Novo Tenant")')
    await expect(page.locator('h2:has-text("Novo Tenant")')).toBeVisible()

    const timestamp = Date.now()
    const tenantKey = `e2e-org-${timestamp}`
    const tenantName = `Org Test E2E ${timestamp}`

    // 2. Fill form
    await page.fill('input[placeholder="ex: acme-corp"]', tenantKey)
    await page.fill('input[placeholder="ex: Acme Corporation"]', tenantName)

    // 3. Submit
    await page.click('button[type="submit"]:has-text("Salvar Organização")')

    // 4. Verify listed in table
    const tenantRow = page.locator(`tr:has-text("${tenantName}")`)
    await expect(tenantRow).toBeVisible()
    await expect(tenantRow.locator('text=Ativo')).toBeVisible()
    await expect(tenantRow.locator(`text=${tenantKey}`)).toBeVisible()

    // 5. Test search filter
    const searchInput = page.locator('input[placeholder*="Buscar"]')
    await searchInput.fill(tenantKey)
    await page.waitForTimeout(400) // allow debounce
    await expect(page.locator(`tr:has-text("${tenantName}")`)).toBeVisible()

    // Clear search
    await searchInput.fill('')
    await page.waitForTimeout(400)

    // 6. Edit Tenant
    await tenantRow.locator('button[title="Editar tenant"]').click()
    await expect(page.locator('h2:has-text("Editar Organização")')).toBeVisible()

    // Key should be disabled when editing
    await expect(page.locator('input[placeholder="ex: acme-corp"]')).toBeDisabled()

    // Update name and change status to disabled
    const updatedName = `${tenantName} Alterada`
    await page.fill('input[placeholder="ex: Acme Corporation"]', updatedName)
    await page.selectOption('select', 'disabled')

    await page.click('button[type="submit"]:has-text("Salvar Alterações")')

    // Verify updated values in table
    const updatedRow = page.locator(`tr:has-text("${updatedName}")`)
    await expect(updatedRow).toBeVisible()
    await expect(updatedRow.locator('text=Desativado')).toBeVisible()
  })

  test('SCN-E2E-PROJECT-01: should create, filter by tenant, and edit a Project', async ({ page }) => {
    await login(page)
    await page.click('aside a[href="/projects"]')
    await expect(page).toHaveURL('/projects')

    // 1. Open "Novo Projeto" Dialog
    await page.click('button:has-text("Novo Projeto")')
    await expect(page.locator('h2:has-text("Novo Projeto")')).toBeVisible()

    const timestamp = Date.now()
    const projectKey = `proj-${timestamp}`
    const projectName = `Microservice E2E ${timestamp}`

    // 2. Fill form
    await page.fill('input[placeholder="ex: payment-service"]', projectKey)
    await page.fill('input[placeholder="ex: Serviço de Pagamentos"]', projectName)

    // 3. Submit
    await page.click('button[type="submit"]:has-text("Salvar Projeto")')

    // 4. Verify listed in table
    const projectRow = page.locator(`tr:has-text("${projectKey}")`)
    await expect(projectRow).toBeVisible()
    await expect(projectRow.locator(`text=${projectName}`)).toBeVisible()

    // 5. Test search filter
    const searchInput = page.locator('input[placeholder*="Buscar"]')
    await searchInput.fill(projectKey)
    await page.waitForTimeout(400) // allow debounce
    await expect(page.locator(`tr:has-text("${projectKey}")`)).toBeVisible()

    // Clear search
    await searchInput.fill('')
    await page.waitForTimeout(400)

    // 6. Edit Project
    await projectRow.locator('button[title="Editar projeto"]').click()
    await expect(page.locator('h2:has-text("Editar Projeto")')).toBeVisible()

    // Tenant and Key should be disabled when editing
    await expect(page.locator('input[placeholder="ex: payment-service"]')).toBeDisabled()

    const updatedProjectName = `${projectName} Updated`
    await page.fill('input[placeholder="ex: Serviço de Pagamentos"]', updatedProjectName)
    await page.click('button[type="submit"]:has-text("Salvar Alterações")')

    // Verify updated name
    const updatedRow = page.locator(`tr:has-text("${projectKey}")`)
    await expect(updatedRow).toBeVisible()
    await expect(updatedRow.locator(`text=${updatedProjectName}`)).toBeVisible()
  })

  test('SCN-E2E-DELETE-01: should enforce typed key confirmation in ConfirmDeleteDialog to delete projects and tenants', async ({
    page,
  }) => {
    await login(page)

    // 1. Create a dedicated project to delete
    await page.click('aside a[href="/projects"]')
    await expect(page).toHaveURL('/projects')

    const timestamp = Date.now()
    const projectKey = `del-proj-${timestamp}`
    const projectName = `Del Proj ${timestamp}`

    await page.click('button:has-text("Novo Projeto")')
    await page.fill('input[placeholder="ex: payment-service"]', projectKey)
    await page.fill('input[placeholder="ex: Serviço de Pagamentos"]', projectName)
    await page.click('button[type="submit"]:has-text("Salvar Projeto")')

    const projectRow = page.locator(`tr:has-text("${projectKey}")`)
    await expect(projectRow).toBeVisible()

    // 2. Trigger Delete Project -> ConfirmDeleteDialog
    await projectRow.locator('button[title="Excluir projeto com confirmação"]').click()
    await expect(page.locator('h3:has-text("Confirmar Exclusão de Projeto")')).toBeVisible()

    const deleteBtn = page.locator('button[type="submit"]:has-text("Excluir Definitivamente")')
    const confirmInput = page.locator('input[placeholder="' + projectKey + '"]')

    // Submit button should be disabled initially
    await expect(deleteBtn).toBeDisabled()

    // Type incorrect key
    await confirmInput.fill('wrong-key')
    await expect(deleteBtn).toBeDisabled()

    // Type exact key
    await confirmInput.fill(projectKey)
    await expect(deleteBtn).toBeEnabled()

    // Confirm deletion
    await deleteBtn.click()
    await expect(page.locator('h3:has-text("Confirmar Exclusão de Projeto")')).not.toBeVisible()

    // Verify removed from table
    await expect(page.locator(`tr:has-text("${projectKey}")`)).not.toBeVisible()

    // 3. Create a dedicated tenant to delete
    await page.click('aside a[href="/tenants"]')
    await expect(page).toHaveURL('/tenants')

    const tenantKey = `del-org-${timestamp}`
    const tenantName = `Del Org ${timestamp}`

    await page.click('button:has-text("Novo Tenant")')
    await page.fill('input[placeholder="ex: acme-corp"]', tenantKey)
    await page.fill('input[placeholder="ex: Acme Corporation"]', tenantName)
    await page.click('button[type="submit"]:has-text("Salvar Organização")')

    const tenantRow = page.locator(`tr:has-text("${tenantName}")`)
    await expect(tenantRow).toBeVisible()

    // 4. Trigger Delete Tenant -> ConfirmDeleteDialog
    await tenantRow.locator('button[title="Excluir tenant com confirmação"]').click()
    await expect(page.locator('h3:has-text("Confirmar Exclusão de Organização")')).toBeVisible()

    const tenantDeleteBtn = page.locator('button[type="submit"]:has-text("Excluir Definitivamente")')
    const tenantConfirmInput = page.locator('input[placeholder="' + tenantKey + '"]')

    // Button disabled initially
    await expect(tenantDeleteBtn).toBeDisabled()

    // Type wrong key
    await tenantConfirmInput.fill('wrong-slug')
    await expect(tenantDeleteBtn).toBeDisabled()

    // Type exact key
    await tenantConfirmInput.fill(tenantKey)
    await expect(tenantDeleteBtn).toBeEnabled()

    // Confirm deletion
    await tenantDeleteBtn.click()
    await expect(page.locator('h3:has-text("Confirmar Exclusão de Organização")')).not.toBeVisible()

    // Verify removed from table
    await expect(page.locator(`tr:has-text("${tenantName}")`)).not.toBeVisible()
  })
})
