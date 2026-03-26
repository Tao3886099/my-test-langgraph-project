/**
 * 无界微前端（Wujie）通信工具
 *
 * 子应用通过 window.$wujie 获取主应用传入的 props 数据。
 *
 * 主应用通过 <WujieVue :props="{ userInfo: { name, avatar, description } }" />
 * 向子应用传递用户信息。
 */

import { useUserStore } from '@/store'

/** wujie 注入到子应用 window 上的对象类型 */
interface WujieInstance {
  props?: {
    userInfo?: {
      name?: string
      avatar?: string
      description?: string
    }
    [key: string]: any
  }
  bus?: {
    $on: (event: string, callback: (...args: any[]) => void) => void
    $emit: (event: string, ...args: any[]) => void
    $off: (event: string, callback?: (...args: any[]) => void) => void
  }
}

declare global {
  interface Window {
    $wujie?: WujieInstance
    __POWERED_BY_WUJIE__?: boolean
  }
}

/**
 * 判断当前是否运行在 wujie 微前端环境中
 */
export function isWujieEnv(): boolean {
  return !!window.__POWERED_BY_WUJIE__
}

/**
 * 获取主应用传递的 props
 */
export function getWujieProps(): WujieInstance['props'] | undefined {
  return window.$wujie?.props
}

/**
 * 从主应用 props 中读取用户信息并写入 chatgpt-web 的 user store。
 * 应在 app mount 之后调用，确保 pinia 已初始化。
 */
export function initWujieUserInfo(): void {
  if (!isWujieEnv())
    return

  const props = getWujieProps()
  if (!props?.userInfo)
    return

  const { name, avatar, description } = props.userInfo
  const userStore = useUserStore()

  const updates: Record<string, string> = {}
  if (name)
    updates.name = name
  if (avatar)
    updates.avatar = avatar
  if (description)
    updates.description = description

  if (Object.keys(updates).length > 0) {
    userStore.updateUserInfo(updates)
    console.log('[Wujie] 已同步主应用用户信息:', updates)
  }
}

/**
 * 监听主应用通过 bus 发送的用户信息更新事件。
 * 可在 App.vue onMounted 中调用，实现实时同步。
 *
 * 主应用发送示例：
 *   window.$wujie?.bus.$emit('update-user-info', { name: '张三', avatar: '...' })
 */
export function listenWujieUserUpdate(): void {
  if (!isWujieEnv())
    return

  const bus = window.$wujie?.bus
  if (!bus)
    return

  bus.$on('update-user-info', (userInfo: { name?: string; avatar?: string; description?: string }) => {
    const userStore = useUserStore()
    const updates: Record<string, string> = {}
    if (userInfo.name)
      updates.name = userInfo.name
    if (userInfo.avatar)
      updates.avatar = userInfo.avatar
    if (userInfo.description)
      updates.description = userInfo.description

    if (Object.keys(updates).length > 0) {
      userStore.updateUserInfo(updates)
      console.log('[Wujie] 收到主应用用户信息更新:', updates)
    }
  })
}
