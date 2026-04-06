import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const STORAGE_KEY = 'reporting_app_guide_v1'

const GuideContext = createContext({
  open: false,
  stepIndex: 0,
  startTour: () => {},
  nextStep: () => {},
  prevStep: () => {},
  completeTour: () => {},
  totalSteps: 6,
})

export function GuideProvider({ children }) {
  const [open, setOpen] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const totalSteps = 6

  useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_KEY) === '1') return
      const t = setTimeout(() => {
        setStepIndex(0)
        setOpen(true)
      }, 700)
      return () => clearTimeout(t)
    } catch {
      /* ignore */
    }
  }, [])

  const startTour = useCallback(() => {
    setStepIndex(0)
    setOpen(true)
  }, [])

  const completeTour = useCallback(() => {
    try {
      localStorage.setItem(STORAGE_KEY, '1')
    } catch {
      /* ignore */
    }
    setOpen(false)
  }, [])

  const nextStep = useCallback(() => {
    setStepIndex((i) => Math.min(i + 1, totalSteps - 1))
  }, [totalSteps])

  const prevStep = useCallback(() => {
    setStepIndex((i) => Math.max(i - 1, 0))
  }, [])

  const value = useMemo(
    () => ({
      open,
      stepIndex,
      startTour,
      nextStep,
      prevStep,
      completeTour,
      totalSteps,
    }),
    [open, stepIndex, startTour, nextStep, prevStep, completeTour, totalSteps]
  )

  return <GuideContext.Provider value={value}>{children}</GuideContext.Provider>
}

export function useGuide() {
  return useContext(GuideContext)
}
