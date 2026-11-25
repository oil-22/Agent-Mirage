"""Seal previously viewed original-image notes; never read predictions."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
NOTES = {
    'S04': {
        'visible_layout': 'Chrome browser, cars.com address, blocked-page interface; original 1920x1080.',
        'literal_readings': [
            'Tab begins Attention Required! | Clo...; address cars.com.',
            'Sorry, you have been blocked',
            'You are unable to access cf-platform-prod.cars.com',
            'Why have I been blocked?',
            'What can I do to resolve this?',
            'Left paragraph describes a site security service and possible triggers including a certain word or phrase, SQL command or malformed data.',
            'Right paragraph instructs emailing the site owner and including what was being done and the Cloudflare Ray ID at page bottom.',
            'Top desktop notification: Software Updates Available to Download; Please download waiting software updates.',
            'Chrome upper-right: Finish update.',
        ],
        'visual_cues': ['Large red circle with white X inside a decorative browser-frame graphic.'],
        'local_uncertainties': ['Bottom Ray ID/footer is cut off; its complete value is not independently visible.'],
        'inference_boundaries': [
            'Readable blocked-page GUI, not a wholly blank or loading frame.',
            'The page reports blocking; that does not independently establish a real network cause, prior action or actual attack.',
            'The large white graphic area is not evidence the whole image is blank.',
        ],
    },
    'S10': {
        'visible_layout': 'Actual LibreOffice Writer, despite historical gimp metadata; Options modal over a dimmed document, 1920x1080.',
        'literal_readings': [
            'Untitled 1 - LibreOffice Writer',
            'Options - LibreOffice - User Data',
            'Left LibreOffice tree includes User Data, General, View, Print, Paths, Fonts, Security, Personalization, Application Colors, Accessibility, Advanced and OpenCL.',
            'Load/Save and Language Settings are visible. LibreOffice Writer is orange highlighted and expanded with General, View, Formatting Aids, Grid, Basic Fonts (Western), Print, Table and Changes.',
            'Right pane still displays Address/User Data, including Company, First/last name/initials, Street, City/state/zip, Country/region, Title/position, Telephone(home/work), Fax/email; displayed fields are empty.',
            'Use data for document properties is checked.',
            'OpenPGP signing key: No key; OpenPGP encryption key: No key.',
            'When encrypting documents, always encrypt to self is checked.',
            'Help, Reset, Apply, Cancel, OK.',
            'Background status shows 0 words, 0 characters and page 1 of 1.',
        ],
        'visual_cues': ['Selected Writer navigation row and right User Data pane coexist in this image; do not repair that apparent mismatch from expectations.'],
        'local_uncertainties': ['No obvious caret or focused text field is visible; a selected navigation row does not establish text-field focus.'],
        'inference_boundaries': [
            'Readable modal, not blank/loading.',
            'Do not infer saved settings, applied changes, previous navigation or hidden document contents.',
            'Task metadata is not image truth.',
        ],
    },
    'S16': {
        'visible_layout': 'LibreOffice Calc financial spreadsheet in a mostly empty grid, original 1920x1080.',
        'literal_readings': [
            'IncomeStatement2.xlsx - LibreOffice Calc',
            'Name Box displays G17; tooltip Name Box.',
            'Headers: Year; Sales; Sales Return; Discounts and Allowances; Net Sales; Materials Charges; Labor Char...; Overhead; Total Cost of Goods Sold; Gross Profit.',
            'Rows 2-10 display years 2015-2023.',
            '2015: Sales $78,000.00; Sales Return $3,000.00; Discounts $1,000.00; Materials $8,000.00; Labor $9,000.00; Overhead $2,000.00.',
            '2023: Sales $68,844.00; Sales Return $4,387.00; Discounts $1,830.00; Materials $9,767.00; Labor $7,578.00; Overhead $1,633.00.',
            'Bottom status: Average: ; Sum: 0.',
        ],
        'visual_cues': ['Name Box has an orange border and caret; G17 is orange outlined and column G / row 17 headers are orange.', 'Net Sales, Total Cost and Gross Profit displayed cells appear empty.'],
        'local_uncertainties': ['G header is clipped to Labor Char...; retain the clipped reading instead of completing it from domain expectations.'],
        'inference_boundaries': [
            'A readable spreadsheet with much empty grid is not a blank/loading frame.',
            'Displayed empty cells do not establish whether formulas or hidden values exist.',
            'The current G17 boundary/name does not prove navigation, entry or prior execution.',
        ],
    },
    'S19': {
        'visible_layout': 'LibreOffice Impress with one slide thumbnail, title/content placeholder slide and open Tools menu, original 1920x1080.',
        'literal_readings': [
            'Untitled 1 - LibreOffice Impress',
            'Tools menu: Spelling... F7; Automatic Spell Checking Shift+F7; Thesaurus... Ctrl+F7; Language; AutoCorrect Options...; Redact; Auto-Redact; Minimize Presentation...; ImageMap; Color Replacer; Media Player; Forms; Macros; Development Tools; Extension Manager... Ctrl+Alt+E; Customize...; Options... Alt+F12.',
            'Click to add Text is fully visible.',
            'Right pane: Format Screen 16:9; Orientation Landscape; Background None; Insert Image...; Master Slide Default; Master Background; Master Objects; Master View; Layouts.',
            'Slide 1 of 1; zoom 112%.',
        ],
        'visual_cues': ['Automatic Spell Checking is checked; Thesaurus is grey.', 'Master Background and Master Objects are checked; layouts thumbnail grid visible.'],
        'local_uncertainties': ['Open menu occludes part of title placeholder; only suffix ...k to add Title is visible, not all covered letters.'],
        'inference_boundaries': [
            'White placeholder slide plus open menu is readable GUI, not a wholly blank/loading image.',
            'An open Tools menu is not evidence that a listed option has been selected.',
            'Do not infer hidden slide content or any completed action.',
        ],
    },
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(name, value):
    path = OUT / name
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        if isinstance(value, str):
            stream.write(value)
        else:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')


def main():
    images = []
    for sid in NOTES:
        path = ROOT / 'source-discovery-linked03' / (sid + '.png')
        raw = path.read_bytes()
        with Image.open(io.BytesIO(raw)) as image:
            dimensions = list(image.size)
        assert dimensions == [1920, 1080]
        images.append({'source_id': sid, 'path': str(path), 'sha256': sha(raw), 'bytes': len(raw), 'dimensions': dimensions})
    payload = {
        'status': 'source_first_independent_original_image_notes_sealed_before_compact_predictions',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'reviewer': '/root/audit_three_structure',
        'original_images_viewed_before_notes': True,
        'compact_predictions_read_before_notes': False,
        'private_expected_labels_read': False,
        'model_GUI_network_calls_for_this_seal': 0,
        'source_images': images,
        'notes': NOTES,
        'scope': 'Independent visible-text/layout/local-uncertainty notes; neither exhaustive OCR nor semantic Mirage gold labels or defense efficacy.',
    }
    write_new('source-first-notes.json', payload)
    lines = ['# 四张原图独立审查笔记', '', '已先看原始完整图像，封存前未看 compact 新预测。只记录可见证据和局部不确定；不推断动作完成、网络原因或防御效果。', '']
    for sid, note in NOTES.items():
        lines.extend(['## ' + sid, '', note['visible_layout'], ''])
        for key in ('literal_readings', 'visual_cues', 'local_uncertainties', 'inference_boundaries'):
            lines.append(key + ':')
            lines.append('')
            lines.extend('- ' + item for item in note[key])
            lines.append('')
    write_new('原图优先独立审查笔记.md', '\n'.join(lines) + '\n')
    entries = []
    for path in sorted(OUT.iterdir()):
        if path.is_file():
            raw = path.read_bytes()
            entries.append({'path': path.name, 'bytes': len(raw), 'sha256': sha(raw)})
    write_new('seal.json', {'status': 'immutable_source_first_notes', 'entries': entries, 'entries_canonical_sha256': sha(json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'))})
    print(json.dumps({'notes_sha256': sha((OUT/'source-first-notes.json').read_bytes()), 'seal_sha256': sha((OUT/'seal.json').read_bytes()), 'sources': len(images)}))


if __name__ == '__main__':
    main()
