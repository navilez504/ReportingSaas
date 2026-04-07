import LegalPageShell from '../components/LegalPageShell'
import { useLanguage } from '../context/LanguageContext'

export default function Terms() {
  const { t } = useLanguage()
  return (
    <LegalPageShell titleKey="legal.termsTitle">
      <div className="space-y-3 whitespace-pre-line">{t('legal.termsBody')}</div>
    </LegalPageShell>
  )
}
