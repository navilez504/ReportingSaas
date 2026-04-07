import LegalPageShell from '../components/LegalPageShell'
import { useLanguage } from '../context/LanguageContext'

export default function Refunds() {
  const { t } = useLanguage()
  return (
    <LegalPageShell titleKey="legal.refundsTitle">
      <div className="space-y-3 whitespace-pre-line">{t('legal.refundsBody')}</div>
    </LegalPageShell>
  )
}
