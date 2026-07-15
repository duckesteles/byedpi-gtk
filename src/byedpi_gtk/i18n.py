import gettext
import locale
import os

DOMAIN = 'byedpi-gtk'

_ORIGINAL_LANGUAGE = os.environ.get('LANGUAGE')

ENDONYMS = {
    'ar': 'العربية',
    'az': 'Azərbaycanca',
    'be': 'Беларуская',
    'bg': 'Български',
    'bn': 'বাংলা',
    'cs': 'Čeština',
    'da': 'Dansk',
    'de': 'Deutsch',
    'el': 'Ελληνικά',
    'en': 'English',
    'es': 'Español',
    'fa': 'فارسی',
    'fi': 'Suomi',
    'fr': 'Français',
    'he': 'עברית',
    'hi': 'हिन्दी',
    'hu': 'Magyar',
    'id': 'Bahasa Indonesia',
    'it': 'Italiano',
    'ja': '日本語',
    'ka': 'ქართული',
    'ko': '한국어',
    'nl': 'Nederlands',
    'pl': 'Polski',
    'pt': 'Português',
    'pt_BR': 'Português (Brasil)',
    'ro': 'Română',
    'ru': 'Русский',
    'sr': 'Српски',
    'sv': 'Svenska',
    'tr': 'Türkçe',
    'uk': 'Українська',
    'vi': 'Tiếng Việt',
    'zh': '中文',
    'zh_CN': '简体中文',
    'zh_TW': '繁體中文',
}


def language_label(code):
    return ENDONYMS.get(code, ENDONYMS.get(code.split('_')[0], code))


def available_languages(localedir):
    found = ['system', 'en']
    if os.path.isdir(localedir):
        for entry in sorted(os.listdir(localedir)):
            mo = os.path.join(localedir, entry, 'LC_MESSAGES', DOMAIN + '.mo')
            if entry not in found and os.path.exists(mo):
                found.append(entry)
    return found


def setup(localedir, override):
    languages = None
    if override and override != 'system':
        languages = [override]
        os.environ['LANGUAGE'] = override
    elif _ORIGINAL_LANGUAGE is None:
        os.environ.pop('LANGUAGE', None)
    else:
        os.environ['LANGUAGE'] = _ORIGINAL_LANGUAGE
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass
    try:
        locale.bindtextdomain(DOMAIN, localedir)
        locale.textdomain(DOMAIN)
    except (AttributeError, ValueError):
        pass
    translation = gettext.translation(
        DOMAIN, localedir, languages=languages, fallback=True
    )
    translation.install(names=['ngettext'])
    return translation
