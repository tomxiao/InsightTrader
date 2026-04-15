<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'

import { adminUsersApi } from '@api/adminUsers'
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import { useAuthStore } from '@stores/auth'
import type { ManagedUser } from '@/types/adminUsers'
import { formatTimeLabel } from '@utils/format'

const router = useRouter()
const authStore = useAuthStore()

const users = ref<ManagedUser[]>([])
const loading = ref(false)
const createSubmitting = ref(false)
const resetSubmitting = ref(false)
const statusSubmittingId = ref<string | null>(null)
const createPopupOpen = ref(false)
const resetPopupOpen = ref(false)
const resetTargetUser = ref<ManagedUser | null>(null)

const createForm = reactive({
  username: '',
  displayName: '',
  password: '',
})

const resetForm = reactive({
  password: '',
})

const isAdmin = computed(() => authStore.isAdmin)
const orderedUsers = computed(() =>
  [...users.value].sort((a, b) => {
    if (a.role !== b.role) return a.role === 'admin' ? -1 : 1
    return a.createdAt.localeCompare(b.createdAt)
  })
)

const loadUsers = async () => {
  loading.value = true
  try {
    users.value = await adminUsersApi.listUsers()
  } catch (error) {
    showToast((error as Error).message || '加载用户列表失败')
  } finally {
    loading.value = false
  }
}

const resetCreateForm = () => {
  createForm.username = ''
  createForm.displayName = ''
  createForm.password = ''
}

const closeCreatePopup = () => {
  createPopupOpen.value = false
  resetCreateForm()
}

const submitCreateUser = async () => {
  const username = createForm.username.trim()
  const displayName = createForm.displayName.trim()
  const password = createForm.password

  if (!username || !password) {
    showToast('请填写用户名和初始密码')
    return
  }

  createSubmitting.value = true
  try {
    const created = await adminUsersApi.createUser({
      username,
      displayName: displayName || undefined,
      password,
    })
    users.value = [created, ...users.value.filter(item => item.id !== created.id)]
    showToast('用户已创建')
    closeCreatePopup()
  } catch (error) {
    showToast((error as Error).message || '创建用户失败')
  } finally {
    createSubmitting.value = false
  }
}

const updateLocalUser = (nextUser: ManagedUser) => {
  users.value = users.value.map(item => item.id === nextUser.id ? nextUser : item)
}

const toggleUserStatus = async (user: ManagedUser) => {
  const nextStatus = user.status === 'active' ? 'disabled' : 'active'
  const actionText = nextStatus === 'disabled' ? '禁用' : '启用'

  try {
    await showConfirmDialog({
      title: `${actionText}用户`,
      message:
        nextStatus === 'disabled'
          ? `确认禁用 ${user.displayName || user.username} 吗？禁用后该账号将无法登录。`
          : `确认启用 ${user.displayName || user.username} 吗？`
    })
  } catch {
    return
  }

  statusSubmittingId.value = user.id
  try {
    const updated = await adminUsersApi.updateUserStatus(user.id, { status: nextStatus })
    updateLocalUser(updated)
    showToast(nextStatus === 'disabled' ? '用户已禁用' : '用户已启用')
  } catch (error) {
    showToast((error as Error).message || `${actionText}用户失败`)
  } finally {
    statusSubmittingId.value = null
  }
}

const openResetPassword = (user: ManagedUser) => {
  resetTargetUser.value = user
  resetForm.password = ''
  resetPopupOpen.value = true
}

const closeResetPopup = () => {
  resetPopupOpen.value = false
  resetTargetUser.value = null
  resetForm.password = ''
}

const submitResetPassword = async () => {
  if (!resetTargetUser.value) return
  if (!resetForm.password) {
    showToast('请填写新密码')
    return
  }

  resetSubmitting.value = true
  try {
    const updated = await adminUsersApi.resetPassword(resetTargetUser.value.id, {
      password: resetForm.password,
    })
    updateLocalUser(updated)
    showToast('密码已重置')
    closeResetPopup()
  } catch (error) {
    showToast((error as Error).message || '重置密码失败')
  } finally {
    resetSubmitting.value = false
  }
}

onMounted(() => {
  if (!isAdmin.value) {
    void router.replace({ name: 'Conversation' })
    return
  }
  void loadUsers()
})
</script>

<template>
  <MobilePageLayout :with-content-padding="false">
    <template #header>
      <div class="admin-users-page__header">
        <van-button plain size="small" class="admin-users-page__back" @click="router.push({ name: 'Conversation' })">
          <van-icon name="arrow-left" />
        </van-button>
        <strong class="admin-users-page__header-title">用户管理</strong>
      </div>
    </template>

    <div class="admin-users-page">
      <section class="admin-users-page__section">
        <div class="admin-users-page__section-head">
          <div class="admin-users-page__section-head-main">
            <h3>用户列表</h3>
            <p>系统内仅保留一个管理员账号，其余账号均按普通用户管理。</p>
          </div>
          <div class="admin-users-page__section-head-actions">
            <span>{{ orderedUsers.length }} 个账号</span>
            <van-button type="primary" round size="small" @click="createPopupOpen = true">新增用户</van-button>
          </div>
        </div>

        <div v-if="loading" class="admin-users-page__empty">正在加载用户列表...</div>
        <div v-else-if="!orderedUsers.length" class="admin-users-page__empty">当前还没有可管理的账号。</div>

        <div v-else class="admin-users-page__list">
          <article v-for="user in orderedUsers" :key="user.id" class="admin-user-card">
            <div class="admin-user-card__top">
              <div class="admin-user-card__identity">
                <strong>{{ user.displayName || user.username }}</strong>
                <small>@{{ user.username }}</small>
              </div>
              <div class="admin-user-card__badges">
                <span
                  class="admin-user-card__badge"
                  :class="user.role === 'admin' ? 'is-admin' : 'is-user'"
                >
                  {{ user.role === 'admin' ? '管理员' : '普通用户' }}
                </span>
                <span
                  class="admin-user-card__badge"
                  :class="user.status === 'active' ? 'is-active' : 'is-disabled'"
                >
                  {{ user.status === 'active' ? '启用中' : '已禁用' }}
                </span>
              </div>
            </div>

            <dl class="admin-user-card__meta">
              <div>
                <dt>创建时间</dt>
                <dd>{{ formatTimeLabel(user.createdAt) || '未知' }}</dd>
              </div>
              <div>
                <dt>最近登录</dt>
                <dd>{{ user.lastLoginAt ? formatTimeLabel(user.lastLoginAt) : '未登录' }}</dd>
              </div>
              <div>
                <dt>最近活跃</dt>
                <dd>{{ user.lastActiveAt ? formatTimeLabel(user.lastActiveAt) : '暂无访问' }}</dd>
              </div>
            </dl>

            <p v-if="user.role === 'admin'" class="admin-user-card__hint">
              系统保留管理员账号，不支持禁用或修改角色。
            </p>

            <div class="admin-user-card__actions">
              <van-button
                plain
                size="small"
                :loading="resetSubmitting && resetTargetUser?.id === user.id"
                @click="openResetPassword(user)"
              >
                重置密码
              </van-button>
              <van-button
                v-if="user.role !== 'admin'"
                size="small"
                plain
                :disabled="statusSubmittingId === user.id"
                :loading="statusSubmittingId === user.id"
                @click="toggleUserStatus(user)"
              >
                {{ user.status === 'active' ? '禁用用户' : '启用用户' }}
              </van-button>
            </div>
          </article>
        </div>
      </section>
    </div>

    <van-popup v-model:show="createPopupOpen" round position="bottom">
      <div class="admin-users-popup">
        <div class="admin-users-popup__head">
          <h3>新增用户</h3>
          <button type="button" class="admin-users-popup__close" aria-label="关闭" @click="closeCreatePopup">
            <van-icon name="cross" />
          </button>
        </div>

        <div class="admin-users-popup__form">
          <van-field v-model="createForm.username" label="用户名" placeholder="请输入用户名" />
          <van-field v-model="createForm.displayName" label="显示名" placeholder="可选，默认与用户名一致" />
          <van-field
            v-model="createForm.password"
            label="初始密码"
            type="password"
            placeholder="至少 8 位"
          />
        </div>

        <div class="admin-users-popup__actions">
          <van-button block plain @click="closeCreatePopup">取消</van-button>
          <van-button block type="primary" :loading="createSubmitting" @click="submitCreateUser">
            创建用户
          </van-button>
        </div>
      </div>
    </van-popup>

    <van-popup v-model:show="resetPopupOpen" round position="bottom">
      <div class="admin-users-popup">
        <div class="admin-users-popup__head">
          <h3>重置密码</h3>
          <button type="button" class="admin-users-popup__close" aria-label="关闭" @click="closeResetPopup">
            <van-icon name="cross" />
          </button>
        </div>

        <p class="admin-users-popup__description">
          为 {{ resetTargetUser?.displayName || resetTargetUser?.username || '该用户' }} 设置新的登录密码。
        </p>

        <div class="admin-users-popup__form">
          <van-field
            v-model="resetForm.password"
            label="新密码"
            type="password"
            placeholder="至少 8 位"
          />
        </div>

        <div class="admin-users-popup__actions">
          <van-button block plain @click="closeResetPopup">取消</van-button>
          <van-button block type="primary" :loading="resetSubmitting" @click="submitResetPassword">
            确认重置
          </van-button>
        </div>
      </div>
    </van-popup>
  </MobilePageLayout>
</template>

<style scoped>
.admin-users-page {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  padding: 0 var(--mobile-space-md) calc(24px + var(--mobile-safe-bottom));
}

.admin-users-page__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px var(--mobile-space-md) 4px;
}

.admin-users-page__back:deep(.van-button) {
  min-width: 36px;
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--mobile-color-text-secondary);
  border-color: rgba(255, 255, 255, 0.08);
}

.admin-users-page__header-title {
  font-size: 14px;
  line-height: 1.25;
}

.admin-users-page__section,
.admin-user-card {
  background: var(--mobile-color-surface);
  border: 1px solid var(--mobile-color-border);
  border-radius: var(--mobile-radius-md);
}

.admin-users-page__section h3,
.admin-users-popup__head h3 {
  margin: 0;
}

.admin-users-page__section {
  padding: 14px;
  margin-top: 12px;
}

.admin-users-page__section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.admin-users-page__section-head-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.admin-users-page__section-head-main p {
  margin: 0;
  color: var(--mobile-color-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.admin-users-page__section-head-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
}

.admin-users-page__section-head span {
  color: var(--mobile-color-text-tertiary);
  font-size: 12px;
}

.admin-users-page__empty {
  color: var(--mobile-color-text-secondary);
  line-height: 1.6;
}

.admin-users-page__list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.admin-user-card {
  padding: 14px;
}

.admin-user-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.admin-user-card__identity {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.admin-user-card__identity strong {
  font-size: 15px;
}

.admin-user-card__identity small {
  color: var(--mobile-color-text-tertiary);
}

.admin-user-card__badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.admin-user-card__badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.admin-user-card__badge.is-admin {
  background: rgba(93, 139, 255, 0.14);
  color: var(--mobile-color-primary-strong);
}

.admin-user-card__badge.is-user {
  background: rgba(255, 255, 255, 0.06);
  color: var(--mobile-color-text-secondary);
}

.admin-user-card__badge.is-active {
  background: rgba(40, 199, 111, 0.14);
  color: #83e5ad;
}

.admin-user-card__badge.is-disabled {
  background: rgba(255, 107, 107, 0.14);
  color: #ff9f9f;
}

.admin-user-card__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0 0;
}

.admin-user-card__meta div {
  min-width: 0;
}

.admin-user-card__meta dt {
  margin: 0 0 4px;
  color: var(--mobile-color-text-tertiary);
  font-size: 11px;
}

.admin-user-card__meta dd {
  margin: 0;
  color: var(--mobile-color-text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.admin-user-card__hint {
  margin: 12px 0 0;
  color: var(--mobile-color-text-tertiary);
  font-size: 12px;
  line-height: 1.5;
}

.admin-user-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.admin-users-popup {
  padding: 18px 16px calc(18px + var(--mobile-safe-bottom));
}

.admin-users-popup__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.admin-users-popup__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--mobile-color-text-secondary);
}

.admin-users-popup__description {
  margin: 12px 0 0;
  color: var(--mobile-color-text-secondary);
  line-height: 1.6;
}

.admin-users-popup__form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.admin-users-popup__actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 18px;
}
</style>
