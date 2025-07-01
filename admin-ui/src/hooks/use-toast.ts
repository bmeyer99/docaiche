import { toast } from "sonner"

type ToastProps = {
  title?: string
  description?: string
  variant?: "default" | "destructive"
  duration?: number
  id?: string
}

export const useToast = () => {
  return {
    toast: ({ title, description, variant, duration, id }: ToastProps) => {
      const options = {
        description,
        duration: duration || 4000,
        id,
      }

      if (variant === "destructive") {
        return toast.error(title || "Error", options)
      } else {
        return toast.success(title || "Info", options)
      }
    },
    dismiss: toast.dismiss,
    warning: (title: string, description?: string, options?: { duration?: number; id?: string }) => {
      return toast.warning(title, {
        description,
        duration: options?.duration || 4000,
        id: options?.id,
      })
    },
    info: (title: string, description?: string, options?: { duration?: number; id?: string }) => {
      return toast.info(title, {
        description,
        duration: options?.duration || 4000,
        id: options?.id,
      })
    },
    error: (title: string, description?: string, options?: { duration?: number; id?: string }) => {
      return toast.error(title, {
        description,
        duration: options?.duration || 4000,
        id: options?.id,
      })
    },
  }
}