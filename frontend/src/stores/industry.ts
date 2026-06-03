import { defineStore } from 'pinia'
import { ref } from 'vue'
import { industryApi, type Industry } from '@/api/industry'

export const useIndustryStore = defineStore('industry', () => {
  const industries = ref<Industry[]>([])
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      const res: any = await industryApi.list()
      industries.value = res.data ?? []
    } finally {
      loading.value = false
    }
  }

  async function create(data: { name: string; description?: string }) {
    await industryApi.create(data)
    await fetchList()
  }

  async function update(slug: string, data: { name?: string; description?: string }) {
    await industryApi.update(slug, data)
    await fetchList()
  }

  async function remove(slug: string) {
    await industryApi.delete(slug)
    await fetchList()
  }

  return { industries, loading, fetchList, create, update, remove }
})