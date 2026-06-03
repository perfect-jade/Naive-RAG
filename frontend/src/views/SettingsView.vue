<template>
  <div class="settings-page">
    <h2>系统配置</h2>

    <el-card class="section-card">
      <template #header><h3>API Key 配置</h3></template>
      <el-form label-width="120px">
        <el-form-item label="DashScope API Key">
          <el-input
            v-model="apiKey"
            type="password"
            show-password
            placeholder="请输入 DashScope API Key"
            @change="handleApiKeyChange"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="section-card">
      <template #header><h3>LLM 模型配置</h3></template>
      <el-radio-group v-model="llmModel" @change="handleLlmChange">
        <el-radio-button
          v-for="m in store.llmModels"
          :key="m.id"
          :value="m.id"
        >
          {{ m.name }}
          <el-tooltip :content="m.description" placement="top">
            <el-icon><InfoFilled /></el-icon>
          </el-tooltip>
        </el-radio-button>
      </el-radio-group>
    </el-card>

    <el-card class="section-card">
      <template #header><h3>Embedding 模型配置</h3></template>
      <el-radio-group v-model="embeddingModel" @change="handleEmbeddingChange">
        <el-radio-button
          v-for="m in store.embeddingModels"
          :key="m.id"
          :value="m.id"
        >
          {{ m.name }} ({{ m.dimension }}维)
          <el-tooltip :content="m.description" placement="top">
            <el-icon><InfoFilled /></el-icon>
          </el-tooltip>
        </el-radio-button>
      </el-radio-group>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSettingsStore } from '@/stores/settings'

const store = useSettingsStore()

const apiKey = ref('')
const llmModel = ref('qwen-plus')
const embeddingModel = ref('text-embedding-v2')

onMounted(async () => {
  await store.fetchSettings()
  await store.fetchModels()

  llmModel.value = store.settings.llm_model
  embeddingModel.value = store.settings.embedding_model
})

async function handleApiKeyChange() {
  try {
    await store.updateSettings({ api_key: apiKey.value })
    ElMessage.success('API Key 已保存')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  }
}

async function handleLlmChange(val: string) {
  try {
    await store.updateSettings({ llm_model: val })
    ElMessage.success('LLM 模型已切换')
  } catch (e: any) {
    ElMessage.error(e.message || '切换失败')
  }
}

async function handleEmbeddingChange(val: string) {
  try {
    ElMessageBox.confirm(
      '切换 Embedding 模型后，已有的知识库向量将无法使用，建议重新录入知识或备份后清空重来。确认切换？',
      '警告',
      { type: 'warning' }
    ).then(async () => {
      const result = await store.updateSettings({ embedding_model: val })
      if (result?.warning) {
        ElMessage.warning(result.warning)
      } else {
        ElMessage.success('Embedding 模型已切换')
      }
    }).catch(() => {
      embeddingModel.value = store.settings.embedding_model
    })
  } catch (e: any) {
    ElMessage.error(e.message || '切换失败')
  }
}
</script>

<style scoped>
.settings-page {
  max-width: 800px;
  margin: 0 auto;
}
.section-card {
  margin-bottom: 20px;
}
.section-card h3 {
  margin: 0;
}
</style>