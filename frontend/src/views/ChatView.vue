<template>
  <div class="chat-page">
    <div class="chat-container">
      <div class="chat-sidebar">
        <div class="sidebar-header">
          <h3>对话历史</h3>
          <el-button size="small" type="primary" @click="startNewChat">新建对话</el-button>
        </div>
        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.id"
            :class="['session-item', { active: currentSessionId === s.id }]"
          >
            <div class="session-content" @click="selectSession(s)">
              <div class="session-title">{{ s.title || '新对话' }}</div>
              <div class="session-meta">{{ s.industry_name || '未分类' }} · {{ s.message_count }} 条</div>
            </div>
            <el-dropdown trigger="click" @command="(cmd: string) => handleSessionCommand(cmd, s)">
              <el-button text size="small" class="session-more-btn">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="delete" divided>删除对话</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <el-empty v-if="sessions.length === 0" description="暂无对话" :image-size="60" />
        </div>
      </div>

      <div class="chat-main">
        <div class="chat-messages" ref="messagesContainer">
          <div v-if="messages.length === 0 && !streaming" class="chat-empty">
            <el-empty description="开始提问吧" :image-size="80" />
          </div>

          <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
            <div class="message-avatar">
              <el-avatar :size="32" :icon="msg.role === 'user' ? UserFilled : Service" />
            </div>
            <div class="message-content">
              <div class="message-text" v-html="renderMarkdown(msg.content)" />
              <div v-if="msg.sources && msg.sources.length > 0" class="message-sources">
                <span class="sources-label">引用来源：</span>
                <span v-for="(s, i) in msg.sources" :key="i" class="source-tag">
                  [{{ i + 1 }}] {{ s.content?.substring(0, 50) }}...
                </span>
              </div>
            </div>
          </div>

          <div v-if="streaming" class="message assistant">
            <div class="message-avatar">
              <el-avatar :size="32" :icon="Service" />
            </div>
            <div class="message-content">
              <div class="message-text" v-html="renderMarkdown(streamContent)" />
              <span class="streaming-cursor">|</span>
            </div>
          </div>
        </div>

        <div class="chat-input-area">
          <div class="industry-indicator" v-if="currentIndustry">
            <el-tag size="small" type="info">{{ currentIndustry }}</el-tag>
          </div>
          <el-input
            v-model="query"
            :rows="2"
            type="textarea"
            placeholder="请输入您的问题..."
            :disabled="streaming"
            @keydown.enter.exact="handleSend"
          />
          <el-button
            type="primary"
            :disabled="!query.trim() || streaming"
            @click="handleSend"
            style="margin-top: 10px"
          >
            <el-icon><Promotion /></el-icon> 发送
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UserFilled, Service } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { chatApi, type ChatSession, type ChatMessage } from '@/api/chat'

interface Message {
  role: string
  content: string
  sources?: Array<{ chunk_id: string; content: string }>
}

const sessions = ref<ChatSession[]>([])
const messages = ref<Message[]>([])
const currentSessionId = ref('')
const currentIndustry = ref('')
const query = ref('')
const streamContent = ref('')
const streaming = ref(false)
const messagesContainer = ref<HTMLElement>()

onMounted(async () => {
  fetchSessions()
})

function renderMarkdown(text: string) {
  return marked.parse(text || '', { breaks: true })
}

async function fetchSessions() {
  try {
    const res: any = await chatApi.getHistory()
    sessions.value = res.data ?? []
  } catch (_) {}
}

function startNewChat() {
  chatApi.createSession().then((res: any) => {
    currentSessionId.value = res.data.id
    messages.value = []
    currentIndustry.value = ''
    streamContent.value = ''
  }).catch(() => {
    messages.value = []
    currentSessionId.value = ''
    currentIndustry.value = ''
    streamContent.value = ''
  })
}

async function selectSession(session: ChatSession) {
  currentSessionId.value = session.id
  currentIndustry.value = session.industry_name || ''
  try {
    const res: any = await chatApi.getSessionMessages(session.id)
    messages.value = (res.data.messages ?? []).map((m: any) => ({
      role: m.role,
      content: m.content,
    }))
  } catch (_) {}
}

async function handleSend() {
  const q = query.value.trim()
  if (!q || streaming.value) return
  query.value = ''
  streamContent.value = ''
  streaming.value = true

  messages.value.push({ role: 'user', content: q })

  // 如果没有 session_id，先创建会话
  if (!currentSessionId.value) {
    try {
      const res: any = await chatApi.createSession()
      currentSessionId.value = res.data.id
    } catch (_) {}
  }

  // 先路由判断
  let routeResult: any = { industry: 'general', slug: 'general' }
  try {
    const res: any = await chatApi.route(q)
    routeResult = res.data ?? routeResult
  } catch (_) {}

  if (routeResult.slug !== 'general') {
    currentIndustry.value = routeResult.industry
  }

  // 流式请求
  const history = messages.value.slice(0, -1).map((m) => ({
    role: m.role,
    content: m.content,
  }))

  let fullAnswer = ''
  const sources: Array<{ chunk_id: string; content: string }> = []

  try {
    const response = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: q,
        history,
        industry: routeResult.slug === 'general' ? null : routeResult.slug,
        session_id: currentSessionId.value || null,
      }),
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (reader) {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'token') {
                fullAnswer += data.data
                streamContent.value = fullAnswer
              } else if (data.type === 'done') {
                if (data.data?.sources) {
                  sources.push(...data.data.sources)
                }
              }
            } catch (_) {}
          }
        }
      }
    }
  } catch (e: any) {
    fullAnswer = streamContent.value || '请求失败，请重试'
  }

  streaming.value = false
  if (fullAnswer) {
    messages.value.push({
      role: 'assistant',
      content: fullAnswer,
      sources,
    })
  }
  streamContent.value = ''

  // 刷新会话列表
  fetchSessions()
  scrollToBottom()
}

function handleSessionCommand(cmd: string, session: ChatSession) {
  if (cmd === 'delete') {
    ElMessageBox.confirm(`确认删除对话「${session.title || '新对话'}」？`, '确认删除', {
      type: 'warning',
    }).then(async () => {
      try {
        await chatApi.deleteSession(session.id)
        ElMessage.success('删除成功')
        sessions.value = sessions.value.filter(s => s.id !== session.id)
        if (currentSessionId.value === session.id) {
          currentSessionId.value = ''
          messages.value = []
          currentIndustry.value = ''
        }
      } catch (e: any) {
        ElMessage.error(e.message || '删除失败')
      }
    }).catch(() => {})
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => messages.value.length, scrollToBottom)
</script>

<style scoped>
.chat-page {
  height: calc(100vh - 60px);
  margin: -20px;
}
.chat-container {
  display: flex;
  height: 100%;
}
.chat-sidebar {
  width: 260px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sidebar-header h3 {
  margin: 0;
  font-size: 15px;
}
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.session-item {
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.session-item:hover, .session-item.active {
  background-color: #ecf5ff;
}
.session-content {
  flex: 1;
  overflow: hidden;
}
.session-more-btn {
  opacity: 0;
}
.session-item:hover .session-more-btn {
  opacity: 1;
}
.session-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.chat-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}
.message {
  display: flex;
  margin-bottom: 20px;
}
.message.user {
  flex-direction: row-reverse;
}
.message-avatar {
  margin: 0 12px;
}
.message-content {
  max-width: 70%;
}
.message.user .message-content {
  background: #ecf5ff;
  padding: 10px 14px;
  border-radius: 12px 4px 12px 12px;
}
.message.assistant .message-content {
  background: #f5f7fa;
  padding: 10px 14px;
  border-radius: 4px 12px 12px 12px;
}
.message-text {
  line-height: 1.6;
  word-break: break-word;
}
.message-text :deep(p) {
  margin: 0 0 8px 0;
}
.message-text :deep(p:last-child) {
  margin-bottom: 0;
}
.message-text :deep(pre) {
  background: #f0f0f0;
  padding: 8px;
  border-radius: 4px;
  overflow-x: auto;
}
.message-text :deep(code) {
  font-size: 13px;
}
.message-sources {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
.source-tag {
  display: inline-block;
  margin-right: 6px;
  background: #e6f7ff;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
}
.streaming-cursor {
  animation: blink 1s infinite;
}
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
.chat-input-area {
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
}
.industry-indicator {
  margin-bottom: 8px;
}
</style>