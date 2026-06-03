import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/industries',
  },
  {
    path: '/industries',
    name: 'Industries',
    component: () => import('@/views/IndustryList.vue'),
  },
  {
    path: '/knowledge/:slug',
    name: 'Knowledge',
    component: () => import('@/views/KnowledgeManage.vue'),
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router