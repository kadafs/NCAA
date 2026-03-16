const FLAG_MAP = {
  England: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', France: '🇫🇷', Germany: '🇩🇪', Spain: '🇪🇸', Italy: '🇮🇹',
  Netherlands: '🇳🇱', Portugal: '🇵🇹', Brazil: '🇧🇷', Argentina: '🇦🇷',
  USA: '🇺🇸', Australia: '🇦🇺', Japan: '🇯🇵', China: '🇨🇳', Korea: '🇰🇷',
  Mexico: '🇲🇽', Colombia: '🇨🇴', Chile: '🇨🇱', Uruguay: '🇺🇾',
  Belgium: '🇧🇪', Turkey: '🇹🇷', Greece: '🇬🇷', Poland: '🇵🇱',
  Russia: '🇷🇺', Ukraine: '🇺🇦', Scotland: '🏴󠁧󠁢󠁳󠁣󠁴󠁿', Ireland: '🇮🇪',
  Sweden: '🇸🇪', Norway: '🇳🇴', Denmark: '🇩🇰', Switzerland: '🇨🇭',
  Austria: '🇦🇹', Romania: '🇷🇴', Serbia: '🇷🇸', Croatia: '🇭🇷',
  'Czech-Republic': '🇨🇿', Hungary: '🇭🇺', Slovakia: '🇸🇰', Bulgaria: '🇧🇬',
  Israel: '🇮🇱', Kazakhstan: '🇰🇿', Armenia: '🇦🇲', Georgia: '🇬🇪',
  Jamaica: '🇯🇲', Rwanda: '🇷🇼', Oman: '🇴🇲', Kuwait: '🇰🇼', Syria: '🇸🇾',
  'United-Arab-Emirates': '🇦🇪', Myanmar: '🇲🇲', India: '🇮🇳',
  World: '🌐',
}

export function flagFor(country) {
  return FLAG_MAP[country] ?? '🌐'
}
