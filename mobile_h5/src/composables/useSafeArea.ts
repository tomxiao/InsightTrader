import { computed } from 'vue'

export const useSafeArea = () => {
  const bottomInset = computed(() => 'env(safe-area-inset-bottom, 0px)')

  return {
    bottomInset
  }
}
