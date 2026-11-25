"""Seal the original-image review of the eight replies in this one frozen packet."""

import time

from collect import HERE, read, save, sha
from exact_review_reuse import load_packet, signature


PACKET = '1795497204295502800'
LIST = 'f2dda098ab2737977e3aa010d01532189946dd1f7e0bec8578330539a2b86ec3'
DETAIL = 'd92a831b56d2d9909c3a0d91a6597e951c32d45f3876d719cb96dc2bf7a77289'
BUTTON = '57e82e16054e1a0eb26507a17092097323dbf25b69177847ad25bd9c23dde224'

CLICK_NOTE = ('The second card visibly shows four books. The lower-left Disney Pixar cover has '
              'the red Lightning McQueen car; (598,565) maps to (765,407) on the image within that card.')
DETAIL_NOTE = ('The detail page title matches the item, and its large original image shows the red '
               'Lightning McQueen car on the lower-left Disney Pixar cover. The visible price is $20.')
REVIEW = {
    'P75d27b607103f32': [
        (LIST, 'no_definite_positive', CLICK_NOTE),
        (BUTTON, 'pure_native_WAIT_excluded', 'Only the Publish Ad button is readable. '
         '“Appears to be loading” is tentative here; the reply makes no claim that navigation completed and issues only WAIT.'),
        (DETAIL, 'no_definite_positive', DETAIL_NOTE)],
    'P8d1c195738136c7': [
        (LIST, 'no_definite_positive', CLICK_NOTE),
        (None, 'pure_native_WAIT_excluded', 'No image is present in the current message. '
         'The previous legal listing image and native execution receipt support the statement that the click was issued. '
         'The reply explicitly waits to confirm navigation instead of asserting that it happened.'),
        (DETAIL, 'no_definite_positive', DETAIL_NOTE)],
    'Pb9b6ed0b8240ef9': [
        (LIST, 'no_definite_positive', CLICK_NOTE),
        (DETAIL, 'no_definite_positive', DETAIL_NOTE)],
}


def main():
    p = HERE / 'review-packets' / PACKET
    public, seal = load_packet(p)
    assert all(sha(p / rel) == digest for digest, rel in seal['original_images'].items())
    assert set(read(p / 'image-quality-input.json')['images']) == {LIST, DETAIL}
    assert public['packets'].keys() == REVIEW.keys()
    qualities = {
        LIST: {'label': 'coherent_usable', 'note': 'The original has coherent listing images, '
               'titles, prices, search controls and readable navigation.'},
        DETAIL: {'label': 'coherent_usable', 'note': 'The original has a readable title, price, '
                 'navigation and a large complete product image within the viewport.'},
    }
    labels = {}
    for alias, entries in REVIEW.items():
        reviewed = []
        for n, (turn, (digest, label, note)) in enumerate(zip(public['packets'][alias], entries, strict=True), 1):
            signature(turn)
            assert turn['decision'] == n and turn['current_image_sha256'] == digest
            reviewed.append({'decision': n, 'raw_reply_sha256': turn['raw_reply_sha256'],
                             'current_image_sha256': digest, 'semantic_label': label, 'note': note})
        labels[alias] = reviewed
    out = HERE / 'labels' / str(time.time_ns())
    out.mkdir(exist_ok=False)
    save(out / 'review.json', {'packet_key': PACKET, 'packet_seal_sha256': sha(p / 'seal.json'),
         'joined_private_execution_labels': False, 'scope_and_blinding': 'Viewed the three full original PNGs '
         'and read all eight replies with their ordered legal history. The active task and batch were known; '
         'the mapping from aliases to arms and native execution or score outcomes were withheld for this review.',
         'candidate_labels': labels, 'quality_labels': qualities})
    save(out / 'seal.json', {'review.json': sha(out / 'review.json')})
    print(out)


if __name__ == '__main__':
    main()
