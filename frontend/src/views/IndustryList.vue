<template>
  <div class="industry-list-page">
    <div class="page-header">
      <h2>行业管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon> 创建行业
      </el-button>
    </div>

    <div v-if="store.loading" class="loading-wrap">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="store.industries.length === 0" class="empty-state">
      <el-empty description="暂无行业，请点击「创建行业」开始" />
    </div>

    <div v-else class="industry-grid">
      <el-card
        v-for="ind in store.industries"
        :key="ind.slug"
        class="industry-card"
        shadow="hover"
        @click="goToKnowledge(ind.slug)"
      >
        <div class="card-header">
          <h3>{{ ind.name }}</h3>
          <el-dropdown trigger="click" @command="(cmd: string) => handleCommand(cmd, ind)">
            <el-button text @click.stop>
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">编辑</el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <p class="card-desc">{{ ind.description || '暂无描述' }}</p>
        <div class="card-footer">
          <span>{{ ind.doc_count }} 篇文档</span>
          <span>{{ ind.chunk_count }} 个分块</span>
        </div>
        <div class="card-chunk-config">
          <span class="config-label">切片配置:</span>
          <span>{{ ind.chunk_size }}/{{ ind.chunk_overlap }}</span>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="showCreateDialog" title="创建行业" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="行业名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入行业名称" />
        </el-form-item>
        <el-form-item label="行业描述" prop="description">
          <el-input v-model="form.description" type="textarea" placeholder="请输入行业描述（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!form.name.trim()" @click="handleCreate">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEditDialog" title="编辑行业" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="行业名称">
          <el-input v-model="editForm.name" placeholder="请输入行业名称" />
        </el-form-item>
        <el-form-item label="行业描述">
          <el-input v-model="editForm.description" type="textarea" placeholder="请输入行业描述" />
        </el-form-item>
        <el-divider />
        <el-form-item label="切片大小">
          <el-input-number 
            v-model="editForm.chunk_size" 
            :min="50" 
            :max="2000" 
            :step="50"
            placeholder="切片大小（字符数）"
          />
          <span style="margin-left: 10px; color: #909399;">字符</span>
        </el-form-item>
        <el-form-item label="重叠大小">
          <el-input-number 
            v-model="editForm.chunk_overlap" 
            :min="0" 
            :max="500" 
            :step="10"
            placeholder="切片重叠大小（字符数）"
          />
          <span style="margin-left: 10px; color: #909399;">字符</span>
        </el-form-item>
        <el-form-item>
          <span style="color: #909399; font-size: 12px;">
            提示：切片大小建议在200-1000字符之间，重叠大小建议为切片大小的10%-20%
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleEdit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useIndustryStore } from '@/stores/industry'
import type { Industry } from '@/api/industry'

const router = useRouter()
const store = useIndustryStore()

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const formRef = ref()
const form = ref({ name: '', description: '' })
const editForm = ref({ name: '', description: '', chunk_size: 500, chunk_overlap: 50 })
const editingSlug = ref('')

const rules = {
  name: [{ required: true, message: '行业名称不能为空', trigger: 'blur' }],
}

onMounted(async () => {
  console.log('IndustryList mounted')
  await store.fetchList()
  console.log('Industries after fetch:', store.industries)
  console.log('Industries length:', store.industries.length)
})

function goToKnowledge(slug: string) {
  router.push(`/knowledge/${slug}`)
}

function handleCommand(cmd: string, ind: Industry) {
  if (cmd === 'edit') {
    editingSlug.value = ind.slug
    editForm.value = { 
      name: ind.name, 
      description: ind.description,
      chunk_size: ind.chunk_size || 500,
      chunk_overlap: ind.chunk_overlap || 50
    }
    showEditDialog.value = true
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(`确认删除行业「${ind.name}」？该操作将删除所有相关数据。`, '确认删除', {
      type: 'warning',
    }).then(async () => {
      await store.remove(ind.slug)
      ElMessage.success('删除成功')
    })
  }
}

async function handleCreate() {
  await formRef.value?.validate()
  try {
    await store.create({ name: form.value.name, description: form.value.description })
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    form.value = { name: '', description: '' }
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  }
}

async function handleEdit() {
  try {
    await store.update(editingSlug.value, {
      name: editForm.value.name,
      description: editForm.value.description,
      chunk_size: editForm.value.chunk_size,
      chunk_overlap: editForm.value.chunk_overlap,
    })
    ElMessage.success('更新成功')
    showEditDialog.value = false
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  }
}
</script>

<style scoped>
.industry-list-page {
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.industry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.industry-card {
  cursor: pointer;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-header h3 {
  font-size: 16px;
  margin: 0;
}
.card-desc {
  color: #909399;
  margin: 10px 0;
  min-height: 40px;
}
.card-footer {
  display: flex;
  justify-content: space-between;
  color: #909399;
  font-size: 13px;
}
.card-chunk-config {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #EBEEF5;
  color: #909399;
  font-size: 12px;
}
.card-chunk-config .config-label {
  margin-right: 4px;
}
.card-chunk-config span:last-child {
  color: #67C23A;
  font-weight: 500;
}
.empty-state, .loading-wrap {
  padding: 60px 0;
}
</style>