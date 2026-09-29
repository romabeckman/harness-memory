import { describe, expect, it } from 'vitest'
import {
  LinkedProjectDto,
  CreateProjectLinkDto,
  validateCreateProjectLinkDto,
} from '@/application/ports/harness-api-client.port'

describe('Project Link DTOs and Contracts', () => {
  it('should validate LinkedProjectDto structure when populated with all mandatory fields', () => {
    const dto: LinkedProjectDto = {
      project_id: 'proj-123',
      key: 'catalog',
      name: 'Catalog Service',
      tenant_id: 'tenant-456',
    }

    expect(dto.project_id).toBe('proj-123')
    expect(dto.key).toBe('catalog')
    expect(dto.name).toBe('Catalog Service')
    expect(dto.tenant_id).toBe('tenant-456')
  })

  it('should validate CreateProjectLinkDto rejects empty target_project_key', () => {
    const invalidDto: CreateProjectLinkDto = {
      target_project_key: '   ',
    }

    const validation = validateCreateProjectLinkDto(invalidDto)
    expect(validation.valid).toBe(false)
    expect(validation.error).toBe('Target project key is required')

    const validDto: CreateProjectLinkDto = {
      target_project_key: 'send',
      target_tenant_id: 'tenant-2',
      created_by: 'user-789',
    }

    const validResult = validateCreateProjectLinkDto(validDto)
    expect(validResult.valid).toBe(true)
    expect(validResult.error).toBeUndefined()
  })

  it('should accept optional created_by field in CreateProjectLinkDto', () => {
    const dto: CreateProjectLinkDto = {
      target_project_key: 'send',
      created_by: 'user-123',
    }
    expect(dto.created_by).toBe('user-123')
  })
})
