<!-- filepath: src/components/AiAssistant/AiEntry.vue -->
<template>
  <!-- 悬浮按钮 -->
  <div class="ai-fab" @click="visible = true" v-show="!visible">
    <el-badge :value="unread" :hidden="!unread">
      <el-button type="primary" circle size="large">
        <el-icon :size="24"><ChatDotRound /></el-icon>
      </el-button>
    </el-badge>
  </div>

  <!-- 侧边抽屉（承载智能体界面） -->
  <el-drawer
    v-model="visible"
    title="智能助手"
    direction="rtl"
    size="60%"
    :show-close="true"
    :with-header="true"
    :destroy-on-close="false"
  >
    <WujieVue
      name="ai-chat"
      style="height: 100%;"
      :url="aiChatUrl"
      :props="wujieProps"
    />
  </el-drawer>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import { useUserStoreHook } from '@/store/modules/user' // 根据实际项目路径调整

const visible = ref(false)
const unread = ref(0)
const aiChatUrl = import.meta.env.VITE_APP_CHAT_URL || 'http://127.0.0.1:1002'

/**
 * 从主应用获取用户信息，通过 wujie props 传递给子应用
 * 请根据你的主应用实际用户 store 调整取值方式
 */
const userStore = useUserStoreHook()

const wujieProps = computed(() => ({
  userInfo: {
    name: userStore.username || userStore.nickname || userStore.name || '',
    avatar: userStore.avatar || '',
    description: userStore.roles?.join(', ') || '',
  },
}))
</script>

<style scoped>
.ai-fab {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 999;
}

.ai-fab .el-button {
  width: 56px;
  height: 56px;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.4);
}

.ai-iframe {
  width: 100%;
  height: calc(100vh - 60px);
  border: none;
}
</style>