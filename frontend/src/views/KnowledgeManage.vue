<template>
  <div class="knowledge-page">
    <div class="page-header">
      <div>
        <el-button text @click="$router.push('/industries')">
          <el-icon><ArrowLeft /></el-icon> 返回行业列表
        </el-button>
        <h2>{{ industryName }} - 知识管理</h2>
      </div>
      <div class="header-actions">
        <el-button @click="showTextDialog = true">
          <el-icon><Edit /></el-icon> 文本录入
        </el-button>
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleFileChange"
          :accept="'.pdf,.docx,.txt,.md'"
          multiple
        >
          <el-button type="primary">
            <el-icon><Upload /></el-icon> 文件上传
          </el-button>
        </el-upload>
      </div>
    </div>

    <el-table :data="documents" border stripe v-loading="loading" empty-text="暂无知识文档">
      <el-table-column prop="title" label="标题" min-width="200">
        <template #default="{ row }">
          {{ row.title || '无标题' }}
        </template>
      </el-table-column>
      <el-table-column prop="source" label="来源" width="80" />
      <el-table-column prop="chunk_count" label="分块数" width="80" />
      <el-table-column prop="tags" label="标签" width="150">
        <template #default="{ row }">
          <el-tag v-for="tag in row.tags" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="录入时间" width="180" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button text @click="showChunks(row)">查看切片</el-button>
          <el-button type="danger" text @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchList"
      />
    </div>

    <el-dialog v-model="showTextDialog" title="文本录入" width="600px">
      <el-form :model="textForm" :rules="textRules" ref="textFormRef" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="textForm.title" placeholder="请输入文档标题（可选）" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="textForm.content" type="textarea" :rows="8" placeholder="请输入文本内容" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="tagInput" placeholder="输入标签后按回车添加" @keyup.enter="addTag">
            <template #prefix>
              <el-tag
                v-for="tag in textForm.tags"
                :key="tag"
                closable
                size="small"
                @close="removeTag(tag)"
                class="tag-item"
              >{{ tag }}</el-tag>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTextDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!textForm.content.trim()" @click="handleTextInsert">确认录入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showUploading" title="文件上传中" width="500px" :close-on-click-modal="false">
      <div v-if="currentStage">
        <div class="stage-container">
          <div 
            v-for="(stage, index) in stages" 
            :key="stage.name"
            :class="['stage-item', { 
              active: currentStageIndex === index,
              done: stage.status === 'success',
              error: stage.status === 'error'
            }]"
          >
            <div class="stage-icon">
              <span v-if="stage.status === 'success'" style="color: #52c41a; font-weight: bold; font-size: 16px;">✓</span>
              <span v-else-if="stage.status === 'error'" style="color: #ff4d4f; font-weight: bold; font-size: 16px;">✗</span>
              <span v-else>{{ index + 1 }}</span>
            </div>
            <div class="stage-info">
              <span class="stage-name">{{ stage.name }}</span>
              <span class="stage-status">{{ stage.statusText }}</span>
            </div>
          </div>
        </div>
      </div>
      <el-progress :percentage="uploadProgress" :status="uploadStatus" style="margin-top: 20px" />
      <p style="margin-top: 10px; text-align: center;">{{ uploadMessage }}</p>
    </el-dialog>

    <el-dialog v-model="showChunksDialog" title="文档切片" width="900px">
      <div v-if="currentDoc">
        <h4 style="margin-bottom: 10px;">{{ currentDoc.title || '无标题' }}</h4>
        <el-table :data="chunks" border v-loading="chunksLoading" empty-text="暂无切片">
          <el-table-column prop="chunk_index" label="序号" width="60" />
          <el-table-column prop="content" label="内容">
            <template #default="{ row }">
              <div class="chunk-content">{{ row.content }}</div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button text size="small" @click="showChunkDetail(row)">查看</el-button>
              <el-button type="danger" text size="small" @click="handleChunkDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <el-dialog v-model="showChunkDetailDialog" title="切片详情" width="700px">
      <div v-if="currentChunk">
        <div class="chunk-detail-header">
          <span class="chunk-index">切片 #{{ currentChunk.chunk_index + 1 }}</span>
          <span class="chunk-length">{{ currentChunk.content.length }} 字符</span>
        </div>
        <div class="chunk-detail-content">
          <pre>{{ currentChunk.content }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { knowledgeApi, type KnowledgeDoc } from '@/api/knowledge'
import { industryApi } from '@/api/industry'

const route = useRoute()
const slug = route.params.slug as string
const industryName = ref('')

const documents = ref<KnowledgeDoc[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const showTextDialog = ref(false)
const showUploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref<'success' | 'exception' | 'warning' | undefined>()
const uploadMessage = ref('')

// 切片相关状态
const showChunksDialog = ref(false)
const showChunkDetailDialog = ref(false)
const currentDoc = ref<KnowledgeDoc | null>(null)
const currentChunk = ref<{ id: string; doc_id: string; content: string; chunk_index: number } | null>(null)
const chunks = ref<Array<{ id: string; doc_id: string; content: string; chunk_index: number }>>([])
const chunksLoading = ref(false)

// 上传阶段状态
interface Stage {
  name: string
  status: 'pending' | 'processing' | 'success' | 'error'
  statusText: string
}

const stages = ref<Stage[]>([
  { name: '读取文件', status: 'pending', statusText: '等待中' },
  { name: '保存文件', status: 'pending', statusText: '等待中' },
  { name: '解析内容', status: 'pending', statusText: '等待中' },
  { name: '分块入库', status: 'pending', statusText: '等待中' },
])
const currentStage = ref('')
const currentStageIndex = ref(-1)

const textFormRef = ref()
const textForm = ref({ title: '', content: '', tags: [] as string[] })
const tagInput = ref('')
const textRules = {
  content: [{ required: true, message: '内容不能为空', trigger: 'blur' }],
}

onMounted(async () => {
  try {
    const res: any = await industryApi.detail(slug)
    industryName.value = res.data.name
  } catch (_) {}
  fetchList()
})

async function fetchList() {
  loading.value = true
  try {
    console.log('Fetching list for slug:', slug)
    const res: any = await knowledgeApi.list(slug, page.value, pageSize.value)
    console.log('API response:', res)
    console.log('res.data:', res.data)
    console.log('res.data.items:', res.data?.items)
    
    const items = res.data.items ?? res.data ?? []
    console.log('Items to set:', items)
    console.log('Items length:', items.length)
    
    documents.value = items
    total.value = res.data.total ?? documents.value.length
    
    console.log('Documents value after assignment:', documents.value)
    console.log('Documents length:', documents.value.length)
    console.log('Documents raw:', JSON.parse(JSON.stringify(documents.value)))
  } catch (e) {
    console.error('Error fetching list:', e)
  } finally {
    loading.value = false
  }
}

function addTag() {
  const tag = tagInput.value.trim()
  if (tag && !textForm.value.tags.includes(tag)) {
    textForm.value.tags.push(tag)
  }
  tagInput.value = ''
}

function removeTag(tag: string) {
  textForm.value.tags = textForm.value.tags.filter((t) => t !== tag)
}

async function handleTextInsert() {
  await textFormRef.value?.validate()
  try {
    await knowledgeApi.insertText(slug, {
      title: textForm.value.title,
      content: textForm.value.content,
      tags: textForm.value.tags,
    })
    ElMessage.success('知识录入成功')
    showTextDialog.value = false
    textForm.value = { title: '', content: '', tags: [] }
    fetchList()
  } catch (e: any) {
    ElMessage.error(e.message || '录入失败')
  }
}

function resetStages() {
  stages.value = [
    { name: '读取文件', status: 'pending', statusText: '等待中' },
    { name: '保存文件', status: 'pending', statusText: '等待中' },
    { name: '解析内容', status: 'pending', statusText: '等待中' },
    { name: '分块入库', status: 'pending', statusText: '等待中' },
  ]
  currentStage.value = ''
  currentStageIndex.value = -1
}

function updateStage(index: number, status: 'processing' | 'success' | 'error', statusText: string = '') {
  if (stages.value[index]) {
    stages.value[index].status = status
    stages.value[index].statusText = statusText || 
      (status === 'processing' ? '处理中...' : 
       status === 'success' ? '完成' : '失败')
    currentStage.value = stages.value[index].name
    currentStageIndex.value = index
    uploadProgress.value = Math.min(95, Math.round((index + 1) * 25))
    uploadMessage.value = `${stages.value[index].name}${status === 'processing' ? '...' : status === 'success' ? '完成' : '失败'}`
  }
}

async function handleFileChange(file: any) {
  showUploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = undefined
  uploadMessage.value = '准备上传...'
  resetStages()

  try {
    // 阶段1: 读取文件
    updateStage(0, 'processing', '正在读取文件内容...')
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // 阶段2: 保存文件
    updateStage(0, 'success')
    updateStage(1, 'processing', '正在保存文件...')
    await new Promise(resolve => setTimeout(resolve, 100))

    // 阶段3: 解析内容
    updateStage(1, 'success')
    updateStage(2, 'processing', '正在解析PDF内容...')

    // 调用上传API
    const result: any = await knowledgeApi.uploadFiles(slug, [file.raw])
    
    // 检查后端返回的阶段状态
    const fileResult = result.data.results?.[0]
    if (fileResult?.status === 'success') {
      // 阶段4: 分块入库
      updateStage(2, 'success')
      updateStage(3, 'processing', '正在分块并入库...')
      await new Promise(resolve => setTimeout(resolve, 300))
      
      updateStage(3, 'success')
      uploadProgress.value = 100
      uploadStatus.value = 'success'
      uploadMessage.value = `上传成功！共 ${fileResult.chunk_count} 个分块`
      ElMessage.success(`文件「${fileResult.filename}」上传成功`)
      
      // 等待1秒后关闭对话框并刷新列表
      setTimeout(() => { 
        showUploading.value = false 
        fetchList()
      }, 1500)
    } else {
      // 上传失败
      const errorStage = fileResult?.stages?.findIndex((s: any) => s.status === 'error')
      if (errorStage >= 0) {
        updateStage(errorStage, 'error', fileResult.error)
      } else {
        updateStage(3, 'error', fileResult?.error || '上传失败')
      }
      uploadStatus.value = 'exception'
      uploadMessage.value = fileResult?.error || '上传失败'
      ElMessage.error(uploadMessage.value)
    }
  } catch (e: any) {
    uploadStatus.value = 'exception'
    uploadMessage.value = e.message || '上传失败'
    // 标记当前阶段为失败
    if (currentStageIndex.value >= 0) {
      stages.value[currentStageIndex.value].status = 'error'
      stages.value[currentStageIndex.value].statusText = uploadMessage.value
    }
    ElMessage.error(uploadMessage.value)
  }
}

async function showChunks(doc: KnowledgeDoc) {
  currentDoc.value = doc
  chunksLoading.value = true
  try {
    const res: any = await knowledgeApi.getDocumentChunks(slug, doc.id)
    chunks.value = res.data || []
  } catch (e: any) {
    ElMessage.error(e.message || '获取切片失败')
    chunks.value = []
  } finally {
    chunksLoading.value = false
    showChunksDialog.value = true
  }
}

function showChunkDetail(chunk: { id: string; doc_id: string; content: string; chunk_index: number }) {
  currentChunk.value = chunk
  showChunkDetailDialog.value = true
}

function handleChunkDelete(chunk: { id: string; doc_id: string }) {
  ElMessageBox.confirm(`确认删除此切片？`, '确认删除', {
    type: 'warning',
  }).then(async () => {
    try {
      await knowledgeApi.deleteChunk(slug, chunk.doc_id, chunk.id)
      ElMessage.success('删除成功')
      chunks.value = chunks.value.filter(c => c.id !== chunk.id)
      fetchList()
    } catch (e: any) {
      ElMessage.error(e.message || '删除失败')
    }
  })
}

function handleDelete(row: KnowledgeDoc) {
  ElMessageBox.confirm(`确认删除文档「${row.title || '无标题'}」？`, '确认删除', {
    type: 'warning',
  }).then(async () => {
    await knowledgeApi.delete(slug, row.id)
    ElMessage.success('删除成功')
    fetchList()
  }).catch(() => {})
}
</script>

<style scoped>
.knowledge-page {
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header-actions {
  display: flex;
  gap: 10px;
}
.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
.tag-item {
  margin-right: 4px;
}

.stage-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stage-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  background: #f8f9fa;
  transition: all 0.3s ease;
}

.stage-item.active {
  background: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.stage-item.done {
  background: #f6ffed;
  border-left: 3px solid #52c41a;
}

.stage-item.error {
  background: #fff2f0;
  border-left: 3px solid #ff4d4f;
}

.stage-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #d9d9d9;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  font-size: 12px;
  font-weight: bold;
  color: #fff;
  transition: all 0.3s ease;
}

.stage-item.done .stage-icon {
  background: #52c41a;
}

.stage-item.error .stage-icon {
  background: #ff4d4f;
}

.stage-item.active .stage-icon {
  background: #1890ff;
}

.stage-info {
  flex: 1;
}

.stage-name {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.stage-status {
  display: block;
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.stage-item.done .stage-status {
  color: #52c41a;
}

.stage-item.error .stage-status {
  color: #ff4d4f;
}

.chunk-content {
  max-height: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

.chunk-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #EBEEF5;
}

.chunk-index {
  font-size: 16px;
  font-weight: 600;
  color: #1f2329;
}

.chunk-length {
  font-size: 14px;
  color: #909399;
}

.chunk-detail-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 12px;
  background-color: #fafafa;
  border-radius: 4px;
}

.chunk-detail-content pre {
  margin: 0;
  font-size: 14px;
  color: #303133;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>