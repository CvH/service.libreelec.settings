# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2020-present Team LibreELEC (https://libreelec.tv)

import os

import config
import os_tools


REGDOMAIN_DEFAULT = 'NOT SET (DEFAULT)'
REGDOMAIN_LIST = [REGDOMAIN_DEFAULT] + [
    "GLOBAL (00)",
    "Afghanistan (AF)",
    "Albania (AL)",
    "Algeria (DZ)",
    "American Samoa (AS)",
    "Andorra (AD)",
    "Anguilla (AI)",
    "Argentina (AR)",
    "Armenia (AM)",
    "Aruba (AW)",
    "Australia (AU)",
    "Austria (AT)",
    "Azerbaijan (AZ)",
    "Bahamas (BS)",
    "Bahrain (BH)",
    "Bangladesh (BD)",
    "Barbados (BB)",
    "Belarus (BY)",
    "Belgium (BE)",
    "Belize (BZ)",
    "Bermuda (BM)",
    "Bhutan (BT)",
    "Bolivia (BO)",
    "Bosnia and Herzegovina (BA)",
    "Brazil (BR)",
    "Brunei Darussalam (BN)",
    "Bulgaria (BG)",
    "Burkina Faso (BF)",
    "Cambodia (KH)",
    "Canada (CA)",
    "Cayman Islands (KY)",
    "Central African Republic (CF)",
    "Chad (TD)",
    "Chile (CL)",
    "China (CN)",
    "Christmas Island (CX)",
    "Colombia (CO)",
    "Costa Rica (CR)",
    "Côte d'Ivoire (CI)",
    "Croatia (HR)",
    "Cuba (CU)",
    "Cyprus (CY)",
    "Czechia (CZ)",
    "Denmark (DK)",
    "Dominica (DM)",
    "Dominican Republic (DO)",
    "Ecuador (EC)",
    "Egypt (EG)",
    "El Salvador (SV)",
    "Estonia (EE)",
    "Ethiopia (ET)",
    "Finland (FI)",
    "France (FR)",
    "French Guiana (GF)",
    "French Polynesia (PF)",
    "Georgia (GE)",
    "Germany (DE)",
    "Ghana (GH)",
    "Greece (GR)",
    "Greenland (GL)",
    "Grenada (GD)",
    "Guadeloupe (GP)",
    "Guam (GU)",
    "Guatemala (GT)",
    "Guyana (GY)",
    "Haiti (HT)",
    "Honduras (HN)",
    "Hong Kong (HK)",
    "Hungary (HU)",
    "Iceland (IS)",
    "India (IN)",
    "Indonesia (ID)",
    "Iran (IR)",
    "Ireland (IE)",
    "Israel (IL)",
    "Italy (IT)",
    "Jamaica (JM)",
    "Japan (JP)",
    "Jordan (JO)",
    "Kazakhstan (KZ)",
    "Kenya (KE)",
    "Korea (North) (KP)",
    "Korea (South) (KR)",
    "Kuwait (KW)",
    "Latvia (LV)",
    "Lebanon (LB)",
    "Lesotho (LS)",
    "Liechtenstein (LI)",
    "Lithuania (LT)",
    "Luxembourg (LU)",
    "Macao (MO)",
    "Malawi (MW)",
    "Malaysia (MY)",
    "Maldives (MV)",
    "Malta (MT)",
    "Marshall Islands (MH)",
    "Martinique (MQ)",
    "Mauritania (MR)",
    "Mauritius (MU)",
    "Mayotte (YT)",
    "Mexico (MX)",
    "Micronesia (FM)",
    "Moldova (MD)",
    "Monaco (MC)",
    "Mongolia (MN)",
    "Montenegro (ME)",
    "Morocco (MA)",
    "Nepal (NP)",
    "Netherlands (NL)",
    "Netherlands Antilles (AN)",
    "New Zealand (NZ)",
    "Nicaragua (NI)",
    "Nigeria (NG)",
    "North Macedonia (MK)",
    "Northern Mariana Islands (MP)",
    "Norway (NO)",
    "Oman (OM)",
    "Pakistan (PK)",
    "Palau (PW)",
    "Panama (PA)",
    "Papua New Guinea (PG)",
    "Paraguay (PY)",
    "Peru (PE)",
    "Philippines (PH)",
    "Poland (PL)",
    "Portugal (PT)",
    "Puerto Rico (PR)",
    "Qatar (QA)",
    "Réunion (RE)",
    "Romania (RO)",
    "Russian Federation (RU)",
    "Rwanda (RW)",
    "Saint Barthélemy (BL)",
    "Saint Kitts and Nevis (KN)",
    "Saint Lucia (LC)",
    "Saint Martin (MF)",
    "Saint Pierre and Miquelon (PM)",
    "Saint Vincent and the Grenadines (VC)",
    "Samoa (WS)",
    "Saudi Arabia (SA)",
    "Senegal (SN)",
    "Serbia (RS)",
    "Singapore (SG)",
    "Slovakia (SK)",
    "Slovenia (SI)",
    "South Africa (ZA)",
    "Spain (ES)",
    "Sri Lanka (LK)",
    "Suriname (SR)",
    "Sweden (SE)",
    "Switzerland (CH)",
    "Syria (SY)",
    "Taiwan (TW)",
    "Tanzania (TZ)",
    "Thailand (TH)",
    "Togo (TG)",
    "Trinidad and Tobago (TT)",
    "Tunisia (TN)",
    "Turkey (TR)",
    "Turks and Caicos Islands (TC)",
    "Uganda (UG)",
    "Ukraine (UA)",
    "United Arab Emirates (AE)",
    "United Kingdom (GB)",
    "United States (US)",
    "Uraguay (UY)",
    "Uzbekistan (UZ)",
    "Vanuatu (VU)",
    "Venezuela (VE)",
    "Vietnam (VN)",
    "Virgin Islands (VI)",
    "Wallis and Futuna (WF)",
    "Yemen (YE)",
    "Zimbabwe (ZW)"
]


def get_regdomain():
    code_suffix = ''
    try:
        with open(config.REGDOMAIN_CONF, 'r', encoding='utf-8') as f:
            line = f.readline().strip()
            if len(line) >= 2: # Ensure line has at least 2 chars for slicing
                # Check if the line has the expected format like REGDOMAIN=XX
                if '=' in line:
                    code_suffix = line.split('=')[-1].strip()
                    if len(code_suffix) > 2: # handle cases like REGDOMAIN=US # United States
                        code_suffix = code_suffix.split(' ')[0]
                    if len(code_suffix) == 2: # Final check for 2 char code
                        pass # code_suffix is good
                    else: # Malformed line or unexpected format
                        config.log.log(f"Regdomain file line content unexpected: {line}", config.log.WARNING)
                        code_suffix = '' # Reset to ensure fallback to default
                elif len(line) == 2: # Assume it's just the code, e.g. "US"
                     code_suffix = line
                else: # Malformed line
                    config.log.log(f"Regdomain file line content not as expected: {line}", config.log.WARNING)
                    code_suffix = ''


    except FileNotFoundError:
        config.log.log(f"File not found: {config.REGDOMAIN_CONF}", config.log.DEBUG)
        # Fall through to return REGDOMAIN_DEFAULT
        pass
    except Exception as e:
        config.log.log(f"Error reading {config.REGDOMAIN_CONF}: {e}", config.log.ERROR)
        # Fall through to return REGDOMAIN_DEFAULT
        pass # Ensure regdomain remains REGDOMAIN_DEFAULT

    if code_suffix and len(code_suffix) == 2:
        code = f'({code_suffix})'
        regdomain = next((l for l in REGDOMAIN_LIST if code in l), REGDOMAIN_DEFAULT)
    else:
        if code_suffix: # Log if there was a suffix but it wasn't 2 chars
             config.log.log(f"Regdomain code '{code_suffix}' from file {config.REGDOMAIN_CONF} is not valid. Falling back to default.", config.log.WARNING)
        regdomain = REGDOMAIN_DEFAULT
    return regdomain


def set_regdomain(regdomain):
    if regdomain == REGDOMAIN_DEFAULT:
        if os.path.isfile(config.REGDOMAIN_CONF):
            try:
                os.remove(config.REGDOMAIN_CONF)
            except (IOError, OSError) as e:
                config.log.log(f"Error removing regdomain file {config.REGDOMAIN_CONF}: {e}", config.log.ERROR)
                return # Skip further operations if removal fails
    else:
        code = regdomain[-3:-1]
        try:
            with open(config.REGDOMAIN_CONF, 'w') as file:
                file.write(f'REGDOMAIN={code}\n')
        except (IOError, OSError) as e:
            config.log.log(f"Error writing regdomain to {config.REGDOMAIN_CONF}: {e}", config.log.ERROR)
            return # Skip service restart if file write fails
    os_tools.execute(config.SETREGDOMAIN)
