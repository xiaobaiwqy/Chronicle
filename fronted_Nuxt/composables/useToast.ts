export function useToast() {
  const message = useState<string>('chronicle-toast-msg', () => '')
  const visible = useState<boolean>('chronicle-toast-visible', () => false)

  let timer: ReturnType<typeof setTimeout> | null = null

  function show(msg: string) {
    message.value = msg
    visible.value = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      visible.value = false
    }, 2200)
  }

  return { message, visible, show }
}
