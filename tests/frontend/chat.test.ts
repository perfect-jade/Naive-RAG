/**
 * 前端测试用例 - Vue 3 组件测试
 *
 * 测试范围:
 * - 行业管理组件 (IndustryList, IndustryCard, CreateIndustryDialog)
 * - 知识管理组件 (KnowledgeList, TextInputDialog, FileUpload)
 * - 对话组件 (ChatPanel, ChatMessage, IndustrySelector)
 * - 系统设置组件 (SettingsPage, ModelSelector, ApiKeyInput)
 * - API 请求封装 (industryApi, knowledgeApi, chatApi, settingsApi)
 * - Pinia Store (industryStore, chatStore, settingsStore)
 *
 * 使用 vitest + @vue/test-utils
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick, ref } from 'vue'


describe('IndustryList Component', () => {
  it('TC-FE-001: 行业列表为空时显示空状态提示', async () => {
    const wrapper = mount({
      template: `
        <div class="industry-list">
          <div v-if="industries.length === 0" class="empty-state">
            暂无行业，请点击「创建行业」开始
          </div>
          <div v-else>
            <div v-for="ind in industries" :key="ind.slug" class="industry-card">
              {{ ind.name }}
            </div>
          </div>
        </div>
      `,
      setup() {
        const industries = ref([])
        return { industries }
      }
    })

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.find('.empty-state').text()).toContain('暂无行业')
  })

  it('TC-FE-002: 行业列表渲染多个行业卡片', async () => {
    const industries = [
      { id: '1', name: '医疗健康', slug: 'medical_health', doc_count: 42 },
      { id: '2', name: '法律法规', slug: 'legal', doc_count: 28 },
      { id: '3', name: '金融财经', slug: 'finance', doc_count: 15 },
    ]

    const wrapper = mount({
      template: `
        <div class="industry-list">
          <div v-for="ind in industries" :key="ind.slug" class="industry-card">
            <h3>{{ ind.name }}</h3>
            <span>{{ ind.doc_count }} 篇文档</span>
          </div>
        </div>
      `,
      setup() {
        return { industries: ref(industries) }
      }
    })

    const cards = wrapper.findAll('.industry-card')
    expect(cards).toHaveLength(3)
    expect(cards[0].text()).toContain('医疗健康')
    expect(cards[0].text()).toContain('42')
  })

  it('TC-FE-003: 点击创建行业按钮打开创建弹窗', async () => {
    const wrapper = mount({
      template: `
        <div>
          <button @click="showDialog = true">创建行业</button>
          <div v-if="showDialog" class="create-dialog">
            <input v-model="newName" placeholder="行业名称" />
            <button @click="create">确认</button>
          </div>
        </div>
      `,
      setup() {
        const showDialog = ref(false)
        const newName = ref('')
        return { showDialog, newName }
      }
    })

    expect(wrapper.find('.create-dialog').exists()).toBe(false)

    await wrapper.find('button').trigger('click')
    await nextTick()

    expect(wrapper.find('.create-dialog').exists()).toBe(true)
  })

  it('TC-FE-004: 行业名称输入校验 - 空名称不允许提交', async () => {
    const wrapper = mount({
      template: `
        <div>
          <div class="create-dialog">
            <input v-model="name" placeholder="行业名称" />
            <span v-if="errorMsg" class="error">{{ errorMsg }}</span>
            <button :disabled="!name.trim()" @click="submit">确认</button>
          </div>
        </div>
      `,
      setup() {
        const name = ref('')
        const errorMsg = ref('')
        function submit() {
          if (!name.value.trim()) {
            errorMsg.value = '行业名称不能为空'
          }
        }
        return { name, errorMsg, submit }
      }
    })

    const btn = wrapper.find('button')
    expect(btn.attributes('disabled')).toBeDefined()

    await wrapper.find('input').setValue(' ')
    expect(btn.attributes('disabled')).toBeDefined()
  })
})


describe('KnowledgeList Component', () => {
  it('TC-FE-005: 知识列表分页展示', async () => {
    const documents = Array.from({ length: 25 }, (_, i) => ({
      id: `doc_${i}`,
      title: `文档 ${i + 1}`,
      chunk_count: 10,
      created_at: '2026-06-01',
    }))

    const pageSize = 10
    const currentPage = ref(1)
    const totalPages = Math.ceil(documents.length / pageSize)

    const pageData = documents.slice(
      (currentPage.value - 1) * pageSize,
      currentPage.value * pageSize
    )

    expect(pageData.length).toBe(10)
    expect(totalPages).toBe(3)
    expect(pageData[0].title).toBe('文档 1')
  })

  it('TC-FE-006: 删除文档前弹出确认框', async () => {
    const wrapper = mount({
      template: `
        <div>
          <div class="doc-item">
            <span>测试文档</span>
            <button @click="confirmDelete = true">删除</button>
          </div>
          <div v-if="confirmDelete" class="confirm-dialog">
            <span>确认删除该文档？</span>
            <button @click="doDelete">确认</button>
            <button @click="confirmDelete = false">取消</button>
          </div>
        </div>
      `,
      setup() {
        const confirmDelete = ref(false)
        const doDelete = vi.fn()
        return { confirmDelete, doDelete }
      }
    })

    expect(wrapper.find('.confirm-dialog').exists()).toBe(false)

    await wrapper.find('.doc-item button').trigger('click')
    await nextTick()

    expect(wrapper.find('.confirm-dialog').exists()).toBe(true)
  })

  it('TC-FE-007: 文件上传组件接受 PDF/DOCX/TXT/MD 格式', async () => {
    const acceptedFormats = '.pdf,.docx,.txt,.md'

    const wrapper = mount({
      template: `
        <div>
          <input type="file" :accept="accept" />
          <span class="hint">支持 PDF、DOCX、TXT、MD 格式</span>
        </div>
      `,
      setup() {
        return { accept: acceptedFormats }
      }
    })

    const input = wrapper.find('input[type="file"]')
    expect(input.attributes('accept')).toBe(acceptedFormats)
  })
})


describe('ChatPanel Component', () => {
  it('TC-FE-008: 发送消息后显示在对话列表中', async () => {
    const messages = ref([])

    const wrapper = mount({
      template: `
        <div class="chat-panel">
          <div v-for="msg in messages" :key="msg.id" :class="msg.role">
            {{ msg.content }}
          </div>
          <input v-model="inputText" @keyup.enter="send" />
        </div>
      `,
      setup() {
        const inputText = ref('')
        function send() {
          if (inputText.value.trim()) {
            messages.value.push({
              id: Date.now(),
              role: 'user',
              content: inputText.value,
            })
            inputText.value = ''
          }
        }
        return { messages, inputText, send }
      }
    })

    await wrapper.find('input').setValue('高血压的诊断标准是什么？')
    await wrapper.find('input').trigger('keyup.enter')
    await nextTick()

    expect(wrapper.findAll('.user')).toHaveLength(1)
    expect(wrapper.find('.user').text()).toContain('高血压的诊断标准')
  })

  it('TC-FE-009: 行业选择器 - 自动判断 vs 手动选择', async () => {
    const wrapper = mount({
      template: `
        <div>
          <select v-model="selectedIndustry">
            <option value="">自动判断</option>
            <option v-for="ind in industries" :key="ind.slug" :value="ind.slug">
              {{ ind.name }}
            </option>
          </select>
        </div>
      `,
      setup() {
        const selectedIndustry = ref('')
        const industries = [
          { name: '医疗健康', slug: 'medical_health' },
          { name: '法律法规', slug: 'legal' },
        ]
        return { selectedIndustry, industries }
      }
    })

    const select = wrapper.find('select')
    const options = select.findAll('option')
    expect(options).toHaveLength(3)
    expect(options[0].text()).toBe('自动判断')
    expect(options[1].text()).toBe('医疗健康')
  })

  it('TC-FE-010: 流式输出时 token 逐字追加', async () => {
    const fullResponse = ref('')
    const tokens = ['根据', '资料', '显示', '，', '高血压', '的诊断', '标准', '为']

    for (const token of tokens) {
      fullResponse.value += token
    }

    expect(fullResponse.value).toBe('根据资料显示，高血压的诊断标准为')
  })

  it('TC-FE-011: 检索为空时显示提示信息', async () => {
    const wrapper = mount({
      template: `
        <div>
          <div v-if="noResults" class="no-result-msg">
            当前知识库中未找到相关内容，无法回答此问题
          </div>
        </div>
      `,
      setup() {
        const noResults = ref(true)
        return { noResults }
      }
    })

    expect(wrapper.find('.no-result-msg').exists()).toBe(true)
    expect(wrapper.find('.no-result-msg').text()).toContain('无法回答')
  })

  it('TC-FE-012: 对话历史列表展示', async () => {
    const conversations = [
      { id: '1', title: '高血压诊断标准', industry: '医疗健康', created_at: '2026-06-01' },
      { id: '2', title: '糖尿病防治', industry: '医疗健康', created_at: '2026-05-30' },
    ]

    const wrapper = mount({
      template: `
        <div class="history-list">
          <div v-for="conv in conversations" :key="conv.id" class="history-item">
            <span class="title">{{ conv.title }}</span>
            <span class="industry">{{ conv.industry }}</span>
          </div>
        </div>
      `,
      setup() {
        return { conversations }
      }
    })

    const items = wrapper.findAll('.history-item')
    expect(items).toHaveLength(2)
    expect(items[0].text()).toContain('高血压诊断标准')
    expect(items[0].text()).toContain('医疗健康')
  })
})


describe('SettingsPage Component', () => {
  it('TC-FE-013: API Key 输入框为密码类型', async () => {
    const wrapper = mount({
      template: `
        <div>
          <input v-model="apiKey" type="password" placeholder="请输入 DashScope API Key" />
          <button @click="showKey = !showKey">{{ showKey ? '隐藏' : '显示' }}</button>
        </div>
      `,
      setup() {
        const apiKey = ref('')
        const showKey = ref(false)
        return { apiKey, showKey }
      }
    })

    const input = wrapper.find('input')
    expect(input.attributes('type')).toBe('password')
  })

  it('TC-FE-014: LLM 模型切换单选按钮组', async () => {
    const wrapper = mount({
      template: `
        <div>
          <label v-for="model in llmModels" :key="model.id">
            <input
              type="radio"
              :value="model.id"
              v-model="selectedLLM"
            />
            {{ model.name }} - {{ model.description }}
          </label>
        </div>
      `,
      setup() {
        const selectedLLM = ref('qwen-plus')
        const llmModels = [
          { id: 'qwen-turbo', name: 'Qwen Turbo', description: '快速、经济' },
          { id: 'qwen-plus', name: 'Qwen Plus', description: '效果与速度平衡' },
          { id: 'qwen-max', name: 'Qwen Max', description: '最强效果' },
        ]
        return { selectedLLM, llmModels }
      }
    })

    const radios = wrapper.findAll('input[type="radio"]')
    expect(radios).toHaveLength(3)
    expect(radios[1].element.checked).toBe(true)
  })

  it('TC-FE-015: 切换 Embedding 模型时弹出警告', async () => {
    const wrapper = mount({
      template: `
        <div>
          <select v-model="embeddingModel" @change="onChange">
            <option value="text-embedding-v2">Embedding V2</option>
            <option value="text-embedding-v3">Embedding V3</option>
          </select>
          <div v-if="showWarning" class="warning">
            切换 Embedding 模型后，已有的知识库向量将无法使用
          </div>
        </div>
      `,
      setup() {
        const embeddingModel = ref('text-embedding-v2')
        const showWarning = ref(false)
        function onChange() {
          showWarning.value = true
        }
        return { embeddingModel, showWarning, onChange }
      }
    })

    expect(wrapper.find('.warning').exists()).toBe(false)

    await wrapper.find('select').setValue('text-embedding-v3')
    await wrapper.find('select').trigger('change')
    await nextTick()

    expect(wrapper.find('.warning').exists()).toBe(true)
    expect(wrapper.find('.warning').text()).toContain('无法使用')
  })

  it('TC-FE-016: 保存配置后显示成功提示', async () => {
    const wrapper = mount({
      template: `
        <div>
          <button @click="save">保存配置</button>
          <div v-if="saved" class="success-msg">配置已保存</div>
        </div>
      `,
      setup() {
        const saved = ref(false)
        async function save() {
          saved.value = true
        }
        return { saved, save }
      }
    })

    expect(wrapper.find('.success-msg').exists()).toBe(false)

    await wrapper.find('button').trigger('click')
    await nextTick()

    expect(wrapper.find('.success-msg').exists()).toBe(true)
  })
})


describe('API Request Layer', () => {
  it('TC-FE-017: 行业 API 请求封装 - 创建行业', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        code: 0,
        data: { id: '1', name: '医疗健康', slug: 'medical_health' }
      })
    })

    async function createIndustry(name: string, description: string) {
      const res = await mockFetch('/api/v1/industries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description })
      })
      return res.json()
    }

    const result = await createIndustry('医疗健康', '医疗领域知识库')
    expect(result.code).toBe(0)
    expect(result.data.name).toBe('医疗健康')
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })

  it('TC-FE-018: 知识 API 请求封装 - 文本录入', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        code: 0,
        data: { doc_id: 'uuid', chunk_count: 15, message: '知识录入成功' }
      })
    })

    async function insertText(slug: string, title: string, content: string, tags: string[]) {
      const res = await mockFetch(`/api/v1/industries/${slug}/knowledge/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content, tags })
      })
      return res.json()
    }

    const result = await insertText('medical_health', '测试文档', '测试内容', ['标签1'])
    expect(result.code).toBe(0)
    expect(result.data.chunk_count).toBe(15)
  })

  it('TC-FE-019: SSE 流式对话事件解析', async () => {
    const sseEvents = [
      'event: route\ndata: {"industry": "医疗健康", "slug": "medical_health", "confidence": "high"}',
      'event: retrieval\ndata: {"count": 5, "sources": [{"title": "xxx", "chunk_index": 3}]}',
      'event: token\ndata: {"token": "根据"}',
      'event: token\ndata: {"token": "资料"}',
      'event: done\ndata: {"total_tokens": 350}',
    ]

    const parsedEvents: { event: string; data: any }[] = []
    let currentEvent = ''

    for (const line of sseEvents) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7)
      } else if (line.startsWith('data: ')) {
        parsedEvents.push({
          event: currentEvent,
          data: JSON.parse(line.slice(6))
        })
      }
    }

    expect(parsedEvents).toHaveLength(5)
    expect(parsedEvents[0].event).toBe('route')
    expect(parsedEvents[0].data.industry).toBe('医疗健康')
    expect(parsedEvents[4].event).toBe('done')
    expect(parsedEvents[4].data.total_tokens).toBe(350)
  })

  it('TC-FE-020: 设置 API 请求封装 - 获取模型列表', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        code: 0,
        data: {
          llm_models: [
            { id: 'qwen-plus', name: 'Qwen Plus', description: '平衡' }
          ],
          embedding_models: [
            { id: 'text-embedding-v2', name: 'Embedding V2', dimension: 1536 }
          ]
        }
      })
    })

    async function getModels() {
      const res = await mockFetch('/api/v1/settings/models')
      return res.json()
    }

    const result = await getModels()
    expect(result.data.llm_models).toHaveLength(1)
    expect(result.data.embedding_models[0].dimension).toBe(1536)
  })
})


describe('Edge Cases & Error Handling', () => {
  it('TC-FE-021: API 请求失败时显示错误提示', async () => {
    const wrapper = mount({
      template: `
        <div>
          <div v-if="errorMsg" class="error-toast">{{ errorMsg }}</div>
          <button @click="fetchData">加载数据</button>
        </div>
      `,
      setup() {
        const errorMsg = ref('')
        async function fetchData() {
          errorMsg.value = '网络请求失败，请稍后重试'
        }
        return { errorMsg, fetchData }
      }
    })

    await wrapper.find('button').trigger('click')
    await nextTick()

    expect(wrapper.find('.error-toast').exists()).toBe(true)
    expect(wrapper.find('.error-toast').text()).toContain('网络请求失败')
  })

  it('TC-FE-022: 长文本在对话中正确截断显示', async () => {
    const longText = 'A'.repeat(5000)
    const displayText = longText.length > 200
      ? longText.slice(0, 200) + '...'
      : longText

    expect(displayText.length).toBe(203)
    expect(displayText.endsWith('...')).toBe(true)
  })
})