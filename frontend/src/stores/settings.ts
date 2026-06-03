import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsApi, type Settings, type ModelItem } from '@/api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<Settings>({
    llm_model: 'qwen-plus',
    embedding_model: 'text-embedding-v2',
    api_key_configured: false,
  })
  const llmModels = ref<ModelItem[]>([])
  const embeddingModels = ref<ModelItem[]>([])
  const loading = ref(false)

  async function fetchSettings() {
    try {
      const res: any = await settingsApi.get()
      settings.value = res.data
    } catch (_) {}
  }

  async function fetchModels() {
    try {
      const res: any = await settingsApi.getModels()
      llmModels.value = res.data.llm_models ?? []
      embeddingModels.value = res.data.embedding_models ?? []
    } catch (_) {}
  }

  async function updateSettings(data: { llm_model?: string; embedding_model?: string; api_key?: string }) {
    const res: any = await settingsApi.update(data)
    await fetchSettings()
    return res.data
  }

  return { settings, llmModels, embeddingModels, loading, fetchSettings, fetchModels, updateSettings }
})