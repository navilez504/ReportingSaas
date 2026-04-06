import { useEffect, useLayoutEffect } from 'react'
import { createPortal } from 'react-dom'
import { useGuide } from '../context/GuideContext'
import { useLanguage } from '../context/LanguageContext'

const STEPS = [
  { titleKey: 'guide.welcomeTitle', bodyKey: 'guide.welcomeBody', target: null },
  { titleKey: 'guide.dashboardTitle', bodyKey: 'guide.dashboardBody', target: 'tour-dashboard' },
  { titleKey: 'guide.uploadTitle', bodyKey: 'guide.uploadBody', target: 'tour-upload' },
  { titleKey: 'guide.reportsTitle', bodyKey: 'guide.reportsBody', target: 'tour-reports' },
  { titleKey: 'guide.languageTitle', bodyKey: 'guide.languageBody', target: 'tour-language' },
  { titleKey: 'guide.doneTitle', bodyKey: 'guide.doneBody', target: null },
]

function clearTourHighlights() {
  document.querySelectorAll('[data-tour-active="true"]').forEach((el) => {
    el.removeAttribute('data-tour-active')
  })
}

export default function GuideTour() {
  const { t } = useLanguage()
  const { open, stepIndex, nextStep, prevStep, completeTour, totalSteps } = useGuide()
  const step = STEPS[stepIndex] ?? STEPS[0]
  const isFirst = stepIndex === 0
  const isLast = stepIndex === totalSteps - 1

  useLayoutEffect(() => {
    if (!open) {
      clearTourHighlights()
      return
    }
    clearTourHighlights()
    const id = step?.target
    if (!id) return undefined
    const el = document.querySelector(`[data-tour="${id}"]`)
    if (!el) return undefined
    el.setAttribute('data-tour-active', 'true')
    el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    return () => {
      el.removeAttribute('data-tour-active')
    }
  }, [open, stepIndex, step?.target])

  useEffect(() => {
    if (!open) return
    function onKey(e) {
      if (e.key === 'Escape') completeTour()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, completeTour])

  if (!open) return null

  const panel = (
    <div
      className="fixed inset-0 z-[100] flex flex-col items-center justify-end sm:justify-center p-4 pointer-events-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="guide-tour-title"
      aria-describedby="guide-tour-desc"
    >
      <div className="absolute inset-0 bg-slate-900/45 backdrop-blur-[1px]" aria-hidden />
      <div
        className="relative z-[120] w-full max-w-md rounded-2xl border border-slate-200/80 bg-white shadow-xl shadow-slate-900/10 p-6 sm:p-7"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-xs font-medium uppercase tracking-wide text-brand-600 mb-2">
          {stepIndex + 1} / {totalSteps}
        </p>
        <h2 id="guide-tour-title" className="text-lg font-semibold text-slate-900">
          {t(step.titleKey)}
        </h2>
        <p id="guide-tour-desc" className="mt-3 text-sm text-slate-600 leading-relaxed">
          {t(step.bodyKey)}
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={completeTour}
            className="text-sm text-slate-500 hover:text-slate-800 underline-offset-2 hover:underline"
          >
            {t('guide.skip')}
          </button>
          <div className="flex gap-2">
            {!isFirst && (
              <button
                type="button"
                onClick={prevStep}
                className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                {t('guide.back')}
              </button>
            )}
            {isLast ? (
              <button
                type="button"
                onClick={completeTour}
                className="px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-500"
              >
                {t('guide.finish')}
              </button>
            ) : (
              <button
                type="button"
                onClick={nextStep}
                className="px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-500"
              >
                {t('guide.next')}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )

  return createPortal(panel, document.body)
}
