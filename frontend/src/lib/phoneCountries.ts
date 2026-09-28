import { getCountries, parsePhoneNumberFromString, type CountryCode } from "libphonenumber-js/mobile";

export type PhoneCountry = {
  iso: string;
  name: string;
  callingCode: string;
};

const allCountryCallingCodes: readonly PhoneCountry[] = [
  { iso: "AC", name: "Ascension Island", callingCode: "247" },
  { iso: "AF", name: "Afghanistan", callingCode: "93" },
  { iso: "AL", name: "Albania", callingCode: "355" },
  { iso: "DZ", name: "Algeria", callingCode: "213" },
  { iso: "AS", name: "American Samoa", callingCode: "1" },
  { iso: "AD", name: "Andorra", callingCode: "376" },
  { iso: "AO", name: "Angola", callingCode: "244" },
  { iso: "AI", name: "Anguilla", callingCode: "1" },
  { iso: "AQ", name: "Antarctica", callingCode: "672" },
  { iso: "AG", name: "Antigua and Barbuda", callingCode: "1" },
  { iso: "AR", name: "Argentina", callingCode: "54" },
  { iso: "AM", name: "Armenia", callingCode: "374" },
  { iso: "AW", name: "Aruba", callingCode: "297" },
  { iso: "AU", name: "Australia", callingCode: "61" },
  { iso: "AT", name: "Austria", callingCode: "43" },
  { iso: "AZ", name: "Azerbaijan", callingCode: "994" },
  { iso: "BH", name: "Bahrain", callingCode: "973" },
  { iso: "BD", name: "Bangladesh", callingCode: "880" },
  { iso: "BB", name: "Barbados", callingCode: "1" },
  { iso: "BY", name: "Belarus", callingCode: "375" },
  { iso: "BE", name: "Belgium", callingCode: "32" },
  { iso: "BZ", name: "Belize", callingCode: "501" },
  { iso: "BJ", name: "Benin", callingCode: "229" },
  { iso: "BM", name: "Bermuda", callingCode: "1" },
  { iso: "BT", name: "Bhutan", callingCode: "975" },
  { iso: "BO", name: "Bolivia (Plurinational State of)", callingCode: "591" },
  { iso: "BQ", name: "Bonaire, Sint Eustatius and Saba", callingCode: "599" },
  { iso: "BA", name: "Bosnia and Herzegovina", callingCode: "387" },
  { iso: "BW", name: "Botswana", callingCode: "267" },
  { iso: "BV", name: "Bouvet Island", callingCode: "47" },
  { iso: "BR", name: "Brazil", callingCode: "55" },
  { iso: "IO", name: "British Indian Ocean Territory", callingCode: "246" },
  { iso: "BN", name: "Brunei Darussalam", callingCode: "673" },
  { iso: "BG", name: "Bulgaria", callingCode: "359" },
  { iso: "BF", name: "Burkina Faso", callingCode: "226" },
  { iso: "BI", name: "Burundi", callingCode: "257" },
  { iso: "CV", name: "Cabo Verde", callingCode: "238" },
  { iso: "KH", name: "Cambodia", callingCode: "855" },
  { iso: "CM", name: "Cameroon", callingCode: "237" },
  { iso: "CA", name: "Canada", callingCode: "1" },
  { iso: "KY", name: "Cayman Islands", callingCode: "1" },
  { iso: "CF", name: "Central African Republic", callingCode: "236" },
  { iso: "TD", name: "Chad", callingCode: "235" },
  { iso: "CL", name: "Chile", callingCode: "56" },
  { iso: "CN", name: "China", callingCode: "86" },
  { iso: "CX", name: "Christmas Island", callingCode: "61" },
  { iso: "CC", name: "Cocos (Keeling) Islands", callingCode: "61" },
  { iso: "CO", name: "Colombia", callingCode: "57" },
  { iso: "BS", name: "Commonwealth of The Bahamas", callingCode: "1" },
  { iso: "MP", name: "Commonwealth of the Northern Mariana Islands", callingCode: "1" },
  { iso: "KM", name: "Comoros", callingCode: "269" },
  { iso: "CK", name: "Cook Islands", callingCode: "682" },
  { iso: "CR", name: "Costa Rica", callingCode: "506" },
  { iso: "HR", name: "Croatia", callingCode: "385" },
  { iso: "CU", name: "Cuba", callingCode: "53" },
  { iso: "CW", name: "Curaçao", callingCode: "599" },
  { iso: "CY", name: "Cyprus", callingCode: "357" },
  { iso: "CZ", name: "Czechia", callingCode: "420" },
  { iso: "CI", name: "Côte d'Ivoire", callingCode: "225" },
  { iso: "CD", name: "Democratic Republic of the Congo", callingCode: "243" },
  { iso: "DK", name: "Denmark", callingCode: "45" },
  { iso: "DJ", name: "Djibouti", callingCode: "253" },
  { iso: "DM", name: "Dominica", callingCode: "1" },
  { iso: "DO", name: "Dominican Republic", callingCode: "1" },
  { iso: "EC", name: "Ecuador", callingCode: "593" },
  { iso: "EG", name: "Egypt", callingCode: "20" },
  { iso: "SV", name: "El Salvador", callingCode: "503" },
  { iso: "GQ", name: "Equatorial Guinea", callingCode: "240" },
  { iso: "ER", name: "Eritrea", callingCode: "291" },
  { iso: "EE", name: "Estonia", callingCode: "372" },
  { iso: "SZ", name: "Eswatini", callingCode: "268" },
  { iso: "ET", name: "Ethiopia", callingCode: "251" },
  { iso: "FK", name: "Falkland Islands", callingCode: "500" },
  { iso: "FO", name: "Faroe Islands", callingCode: "298" },
  { iso: "FJ", name: "Fiji", callingCode: "679" },
  { iso: "FI", name: "Finland", callingCode: "358" },
  { iso: "FR", name: "France", callingCode: "33" },
  { iso: "GF", name: "French Guiana", callingCode: "594" },
  { iso: "PF", name: "French Polynesia", callingCode: "689" },
  { iso: "TF", name: "French Southern and Antarctic Lands", callingCode: "672" },
  { iso: "GA", name: "Gabon", callingCode: "241" },
  { iso: "GM", name: "Gambia", callingCode: "220" },
  { iso: "GE", name: "Georgia", callingCode: "995" },
  { iso: "DE", name: "Germany", callingCode: "49" },
  { iso: "GH", name: "Ghana", callingCode: "233" },
  { iso: "GI", name: "Gibraltar", callingCode: "350" },
  { iso: "GR", name: "Greece", callingCode: "30" },
  { iso: "GL", name: "Greenland", callingCode: "299" },
  { iso: "GD", name: "Grenada", callingCode: "1" },
  { iso: "GP", name: "Guadeloupe", callingCode: "590" },
  { iso: "GU", name: "Guam", callingCode: "1" },
  { iso: "GT", name: "Guatemala", callingCode: "502" },
  { iso: "GG", name: "Guernsey", callingCode: "44" },
  { iso: "GN", name: "Guinea", callingCode: "224" },
  { iso: "GW", name: "Guinea-Bissau", callingCode: "245" },
  { iso: "GY", name: "Guyana", callingCode: "592" },
  { iso: "HT", name: "Haiti", callingCode: "509" },
  { iso: "VA", name: "Holy See", callingCode: "39" },
  { iso: "HN", name: "Honduras", callingCode: "504" },
  { iso: "HK", name: "Hong Kong", callingCode: "852" },
  { iso: "HU", name: "Hungary", callingCode: "36" },
  { iso: "IS", name: "Iceland", callingCode: "354" },
  { iso: "IN", name: "India", callingCode: "91" },
  { iso: "ID", name: "Indonesia", callingCode: "62" },
  { iso: "IR", name: "Iran (Islamic Republic of)", callingCode: "98" },
  { iso: "IQ", name: "Iraq", callingCode: "964" },
  { iso: "IE", name: "Ireland", callingCode: "353" },
  { iso: "IM", name: "Isle of Man", callingCode: "44" },
  { iso: "IL", name: "Israel", callingCode: "972" },
  { iso: "IT", name: "Italy", callingCode: "39" },
  { iso: "JM", name: "Jamaica", callingCode: "1" },
  { iso: "JP", name: "Japan", callingCode: "81" },
  { iso: "JE", name: "Jersey", callingCode: "44" },
  { iso: "JO", name: "Jordan", callingCode: "962" },
  { iso: "KZ", name: "Kazakhstan", callingCode: "7" },
  { iso: "KE", name: "Kenya", callingCode: "254" },
  { iso: "KI", name: "Kiribati", callingCode: "686" },
  { iso: "KW", name: "Kuwait", callingCode: "965" },
  { iso: "KG", name: "Kyrgyzstan", callingCode: "996" },
  { iso: "LA", name: "Lao People's Democratic Republic", callingCode: "856" },
  { iso: "LV", name: "Latvia", callingCode: "371" },
  { iso: "LB", name: "Lebanon", callingCode: "961" },
  { iso: "LS", name: "Lesotho", callingCode: "266" },
  { iso: "LR", name: "Liberia", callingCode: "231" },
  { iso: "LY", name: "Libya", callingCode: "218" },
  { iso: "LI", name: "Liechtenstein", callingCode: "423" },
  { iso: "LT", name: "Lithuania", callingCode: "370" },
  { iso: "LU", name: "Luxembourg", callingCode: "352" },
  { iso: "MO", name: "Macao", callingCode: "853" },
  { iso: "MG", name: "Madagascar", callingCode: "261" },
  { iso: "MW", name: "Malawi", callingCode: "265" },
  { iso: "MY", name: "Malaysia", callingCode: "60" },
  { iso: "MV", name: "Maldives", callingCode: "960" },
  { iso: "ML", name: "Mali", callingCode: "223" },
  { iso: "MT", name: "Malta", callingCode: "356" },
  { iso: "MQ", name: "Martinique", callingCode: "596" },
  { iso: "MR", name: "Mauritania", callingCode: "222" },
  { iso: "MU", name: "Mauritius", callingCode: "230" },
  { iso: "YT", name: "Mayotte", callingCode: "262" },
  { iso: "MX", name: "Mexico", callingCode: "52" },
  { iso: "FM", name: "Micronesia (Federated States of)", callingCode: "691" },
  { iso: "MC", name: "Monaco", callingCode: "377" },
  { iso: "MN", name: "Mongolia", callingCode: "976" },
  { iso: "ME", name: "Montenegro", callingCode: "382" },
  { iso: "MS", name: "Montserrat", callingCode: "1" },
  { iso: "MA", name: "Morocco", callingCode: "212" },
  { iso: "MZ", name: "Mozambique", callingCode: "258" },
  { iso: "MM", name: "Myanmar", callingCode: "95" },
  { iso: "NA", name: "Namibia", callingCode: "264" },
  { iso: "NR", name: "Nauru", callingCode: "674" },
  { iso: "NP", name: "Nepal", callingCode: "977" },
  { iso: "NL", name: "Netherlands", callingCode: "31" },
  { iso: "NC", name: "New Caledonia", callingCode: "687" },
  { iso: "NZ", name: "New Zealand", callingCode: "64" },
  { iso: "NI", name: "Nicaragua", callingCode: "505" },
  { iso: "NE", name: "Niger", callingCode: "227" },
  { iso: "NG", name: "Nigeria", callingCode: "234" },
  { iso: "NU", name: "Niue", callingCode: "683" },
  { iso: "NF", name: "Norfolk Island", callingCode: "672" },
  { iso: "KP", name: "North Korea", callingCode: "850" },
  { iso: "MK", name: "North Macedonia", callingCode: "389" },
  { iso: "NO", name: "Norway", callingCode: "47" },
  { iso: "OM", name: "Oman", callingCode: "968" },
  { iso: "PK", name: "Pakistan", callingCode: "92" },
  { iso: "PW", name: "Palau", callingCode: "680" },
  { iso: "PS", name: "Palestine, State of", callingCode: "970" },
  { iso: "PA", name: "Panama", callingCode: "507" },
  { iso: "PG", name: "Papua New Guinea", callingCode: "675" },
  { iso: "PY", name: "Paraguay", callingCode: "595" },
  { iso: "PE", name: "Peru", callingCode: "51" },
  { iso: "PH", name: "Philippines", callingCode: "63" },
  { iso: "PN", name: "Pitcairn", callingCode: "64" },
  { iso: "PL", name: "Poland", callingCode: "48" },
  { iso: "PT", name: "Portugal", callingCode: "351" },
  { iso: "PR", name: "Puerto Rico", callingCode: "1" },
  { iso: "QA", name: "Qatar", callingCode: "974" },
  { iso: "XK", name: "Republic of Kosovo", callingCode: "383" },
  { iso: "MD", name: "Republic of Moldova", callingCode: "373" },
  { iso: "SM", name: "Republic of San Marino", callingCode: "378" },
  { iso: "CG", name: "Republic of the Congo", callingCode: "242" },
  { iso: "MH", name: "Republic of the Marshall Islands", callingCode: "692" },
  { iso: "RO", name: "Romania", callingCode: "40" },
  { iso: "RU", name: "Russia", callingCode: "7" },
  { iso: "RW", name: "Rwanda", callingCode: "250" },
  { iso: "RE", name: "Réunion", callingCode: "262" },
  { iso: "BL", name: "Saint Barthélemy", callingCode: "590" },
  { iso: "SH", name: "Saint Helena, Ascension and Tristan da Cunha", callingCode: "290" },
  { iso: "KN", name: "Saint Kitts and Nevis", callingCode: "1" },
  { iso: "LC", name: "Saint Lucia", callingCode: "1" },
  { iso: "MF", name: "Saint Martin (French part)", callingCode: "590" },
  { iso: "PM", name: "Saint Pierre and Miquelon", callingCode: "508" },
  { iso: "VC", name: "Saint Vincent and the Grenadines", callingCode: "1" },
  { iso: "WS", name: "Samoa", callingCode: "685" },
  { iso: "ST", name: "Sao Tome and Principe", callingCode: "239" },
  { iso: "SA", name: "Saudi Arabia", callingCode: "966" },
  { iso: "SN", name: "Senegal", callingCode: "221" },
  { iso: "RS", name: "Serbia", callingCode: "381" },
  { iso: "SC", name: "Seychelles", callingCode: "248" },
  { iso: "SL", name: "Sierra Leone", callingCode: "232" },
  { iso: "SG", name: "Singapore", callingCode: "65" },
  { iso: "SX", name: "Sint Maarten (Dutch part)", callingCode: "1" },
  { iso: "SK", name: "Slovakia", callingCode: "421" },
  { iso: "SI", name: "Slovenia", callingCode: "386" },
  { iso: "SB", name: "Solomon Islands", callingCode: "677" },
  { iso: "SO", name: "Somalia", callingCode: "252" },
  { iso: "ZA", name: "South Africa", callingCode: "27" },
  { iso: "GS", name: "South Georgia and the South Sandwich Islands", callingCode: "500" },
  { iso: "KR", name: "South Korea", callingCode: "82" },
  { iso: "SS", name: "South Sudan", callingCode: "211" },
  { iso: "ES", name: "Spain", callingCode: "34" },
  { iso: "LK", name: "Sri Lanka", callingCode: "94" },
  { iso: "SD", name: "Sudan", callingCode: "249" },
  { iso: "SR", name: "Suriname", callingCode: "597" },
  { iso: "SJ", name: "Svalbard and Jan Mayen", callingCode: "47" },
  { iso: "SE", name: "Sweden", callingCode: "46" },
  { iso: "CH", name: "Switzerland", callingCode: "41" },
  { iso: "SY", name: "Syrian Arab Republic", callingCode: "963" },
  { iso: "TW", name: "Taiwan, Province of China", callingCode: "886" },
  { iso: "TJ", name: "Tajikistan", callingCode: "992" },
  { iso: "HM", name: "Territory of Heard Island and McDonald Islands", callingCode: "672" },
  { iso: "TH", name: "Thailand", callingCode: "66" },
  { iso: "TL", name: "Timor-Leste", callingCode: "670" },
  { iso: "TG", name: "Togo", callingCode: "228" },
  { iso: "TK", name: "Tokelau", callingCode: "690" },
  { iso: "TO", name: "Tonga", callingCode: "676" },
  { iso: "TT", name: "Trinidad and Tobago", callingCode: "1" },
  { iso: "TN", name: "Tunisia", callingCode: "216" },
  { iso: "TM", name: "Turkmenistan", callingCode: "993" },
  { iso: "TC", name: "Turks and Caicos Islands", callingCode: "1" },
  { iso: "TV", name: "Tuvalu", callingCode: "688" },
  { iso: "TR", name: "Türkiye", callingCode: "90" },
  { iso: "UG", name: "Uganda", callingCode: "256" },
  { iso: "UA", name: "Ukraine", callingCode: "380" },
  { iso: "AE", name: "United Arab Emirates", callingCode: "971" },
  { iso: "GB", name: "United Kingdom", callingCode: "44" },
  { iso: "TZ", name: "United Republic of Tanzania", callingCode: "255" },
  { iso: "UM", name: "United States Minor Outlying Islands", callingCode: "1" },
  { iso: "US", name: "United States of America", callingCode: "1" },
  { iso: "UY", name: "Uruguay", callingCode: "598" },
  { iso: "UZ", name: "Uzbekistan", callingCode: "998" },
  { iso: "VU", name: "Vanuatu", callingCode: "678" },
  { iso: "VE", name: "Venezuela (Bolivarian Republic of)", callingCode: "58" },
  { iso: "VN", name: "Vietnam", callingCode: "84" },
  { iso: "VG", name: "Virgin Islands (British)", callingCode: "1" },
  { iso: "VI", name: "Virgin Islands (U.S.)", callingCode: "1" },
  { iso: "WF", name: "Wallis and Futuna", callingCode: "681" },
  { iso: "EH", name: "Western Sahara", callingCode: "212" },
  { iso: "YE", name: "Yemen", callingCode: "967" },
  { iso: "ZM", name: "Zambia", callingCode: "260" },
  { iso: "ZW", name: "Zimbabwe", callingCode: "263" },
  { iso: "AX", name: "Åland Islands", callingCode: "358" },
  { iso: "TA", name: "Tristan da Cunha", callingCode: "290" },
];

const supportedCountryCodes = new Set<string>(getCountries());
export const countryCallingCodes = allCountryCallingCodes.filter((country) => supportedCountryCodes.has(country.iso));

// libphonenumber-js models these territories on their shared parent numbering plan.
const sharedPlanParentCountries: Readonly<Record<string, string>> = {
  AX: "FI",
  BL: "GP",
  CC: "AU",
  CX: "AU",
  EH: "MA",
  IM: "GB",
  MF: "GP",
  SJ: "NO",
  VA: "IT",
};

export const defaultCountryIso = "TN";

type RegionDisplayNames = { of: (code: string) => string | undefined };
type DisplayNamesConstructor = new (locales: string[], options: { type: "region" }) => RegionDisplayNames;

const displayNamesCache = new Map<string, RegionDisplayNames>();

function getRegionDisplayNames(language: "en" | "fr") {
  const cached = displayNamesCache.get(language);
  if (cached) return cached;

  const DisplayNames = (Intl as typeof Intl & { DisplayNames?: DisplayNamesConstructor }).DisplayNames;
  if (!DisplayNames) return null;

  try {
    const displayNames = new DisplayNames([language], { type: "region" });
    displayNamesCache.set(language, displayNames);
    return displayNames;
  } catch {
    return null;
  }
}

export function getCountryName(country: PhoneCountry, language: "en" | "fr") {
  return getRegionDisplayNames(language)?.of(country.iso) ?? country.name;
}

export function getCountryFlag(iso: string) {
  return [...iso.toUpperCase()]
    .map((letter) => String.fromCodePoint(127397 + letter.charCodeAt(0)))
    .join("");
}

export function normalizePhoneNumber(value: string, callingCode: string, countryIso: string) {
  const trimmedValue = value.trim();
  if (!trimmedValue) return "";

  const parsedPhone = supportedCountryCodes.has(countryIso)
    ? parsePhoneNumberFromString(trimmedValue, countryIso as CountryCode)
    : null;
  if (parsedPhone) return parsedPhone.number;

  const digits = trimmedValue.replace(/\D/g, "");
  if (!digits) return "";
  return trimmedValue.startsWith("+") ? `+${digits}` : `+${callingCode}${digits}`;
}

export function isValidPhoneNumber(value: string, callingCode: string, countryIso: string) {
  if (!supportedCountryCodes.has(countryIso)) return false;
  const normalizedPhone = normalizePhoneNumber(value, callingCode, countryIso);
  if (!normalizedPhone.startsWith(`+${callingCode}`)) return false;

  const parsedPhone = parsePhoneNumberFromString(normalizedPhone);
  // libphonenumber may report a shared-plan territory's parent country.
  const parsedCountry = parsedPhone?.country;
  return Boolean(parsedPhone?.isValid() && (parsedCountry === countryIso || sharedPlanParentCountries[countryIso] === parsedCountry));
}
