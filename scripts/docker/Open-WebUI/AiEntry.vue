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
    class="ai-drawer"
  >
    <div class="ai-chat-container">
      <iframe
        src="http://localhost:1002/sso-login?user_email=xxx&user_name=张三"
        class="ai-iframe"
        allow="clipboard-write; microphone; camera"
        referrerpolicy="origin"
      />
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ChatDotRound } from "@element-plus/icons-vue";
import { computed, ref } from "vue";
import useUserStore from "@/store/modules/user";

const visible = ref(false);
const unread = ref(0);

const userStore = useUserStore();

/**
 * 构建带用户身份查询参数的 Open WebUI URL
 *
 * 原理（方案 B - iframe URL 传参）：
 * 1. 将业务系统的登录用户信息编码到 iframe 的 URL 查询参数中
 * 2. nginx 从 $arg_user_email / $arg_user_name 中提取参数
 * 3. nginx 将参数值设置到 X-User-Email / X-User-Name 请求头
 * 4. Open WebUI 的 Trusted Header Auth 据此自动识别/创建用户
 *
 * 优点：无需 JS 拦截，无需 wujie，原生 iframe 即可，兼容性最好
 */
const iframeSrc = computed(() => {
  // const baseUrl = (
  //   import.meta.env.VITE_APP_CHAT_URL || "http://localhost:1002"
  // ).replace(/\/+$/, "");

  // const email = userStore.email || `${userStore.userId}@gangda.com`;
  // const name = userStore.nickName || userStore.userName || "未知用户";

  // // 先访问 /sso-login 中转页，设置身份 Cookie 后自动跳转到 Open WebUI 首页
  // const url = new URL(`${baseUrl}/sso-login`);
  // url.searchParams.set("user_email", email);
  // url.searchParams.set("user_name", name);
  // return url.toString();
  return 'http://localhost:1002/sso-login?user_email=xxx&user_name=张三'
});
console.log('iframeSrc',iframeSrc);


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

/* AI 聊天容器：撑满 drawer 内容区 */
.ai-chat-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.ai-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>

<style>
/* 非 scoped：覆盖 el-drawer 内部样式，让内容区撑满 */
.ai-drawer .el-drawer__body {
  padding: 0 !important;
  overflow: hidden;
  height: 0;
  flex: 1;
}
</style>
