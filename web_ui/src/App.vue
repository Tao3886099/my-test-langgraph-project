<script setup lang="ts">
import { onMounted } from 'vue'
import { NConfigProvider } from 'naive-ui'
import { NaiveProvider } from '@/components/common'
import { useTheme } from '@/hooks/useTheme'
import { useLanguage } from '@/hooks/useLanguage'
import { listenWujieUserUpdate } from '@/utils/wujie'

const { theme, themeOverrides } = useTheme()
const { language } = useLanguage()

onMounted(() => {
  // 监听主应用通过 bus 推送的用户信息变更
  listenWujieUserUpdate()
})
</script>

<template>
  <NConfigProvider
    class="h-full"
    :theme="theme"
    :theme-overrides="themeOverrides"
    :locale="language"
  >
    <NaiveProvider>
      <RouterView />
    </NaiveProvider>
  </NConfigProvider>
</template>
