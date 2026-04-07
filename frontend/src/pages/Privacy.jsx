import LegalPageShell from '../components/LegalPageShell'
import { useLanguage } from '../context/LanguageContext'

export default function Privacy() {
  const { t } = useLanguage()
  return (
    <LegalPageShell titleKey="legal.privacyTitle">
      <div className="space-y-3 whitespace-pre-line">{t('legal.privacyBody')}</div>
    </LegalPageShell>
  )
}
