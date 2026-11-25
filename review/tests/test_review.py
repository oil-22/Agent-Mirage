import base64
from io import BytesIO
import json
from pathlib import Path
import tempfile
import time
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from PIL import Image
from defense import gate_core as g, receipt_protocol as rp, temporal_controller as tc
from defense.temporal_request import native_request
from defense.wire_contract import decode_request
from observations import intervene
from reproduce import benchmark, defense


def png(color):
    b=BytesIO(); Image.new("RGB",(8,8),color).save(b,format="PNG"); return b.getvalue()


class ReviewChecks(unittest.TestCase):
    def test_four_injections(self):
        now, old = png("red"), png("blue")
        self.assertIsNone(intervene(now,"silent_drop"))
        self.assertEqual(intervene(now,"stale_replace",previous=old),old)
        white = Image.open(BytesIO(intervene(now,"blank_replace")))
        self.assertEqual(white.getextrema(),((255,255),(255,255),(255,255)))
        masked = Image.open(BytesIO(intervene(now,"buttons_only",control_boxes=[(0,0,500,500)])))
        self.assertEqual(masked.getpixel((3,3)),(255,0,0))
        self.assertEqual(masked.getpixel((4,3)),(255,255,255))
        with self.assertRaises(ValueError):
            intervene(now,"stale_replace")

    def test_wire_and_temporal_input_isolation(self):
        old, now = png("navy"),png("white")
        wire={"request_id":"1"*32,"image_png_base64":base64.b64encode(now).decode(),"image_sha256":g.digest(now)}
        self.assertEqual(decode_request(json.dumps(wire))[1],now)
        with self.assertRaises(ValueError):
            decode_request(json.dumps({**wire,"history":"an unsupported premise"}))
        action={"type":"scroll","direction":"down"}
        request=native_request(old,action,now)
        self.assertEqual([base64.b64decode(u.split(",",1)[1]) for u in request["images"]],[old,now])
        with self.assertRaises(ValueError):
            native_request(old,{**action,"thought":"hidden"},now)

    def test_receipts_and_actual_recapture_handoff(self):
        old, now = png("red"),png("green")
        key=Ed25519PrivateKey.generate()
        pub=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            verifier=rp.ReceiptVerifier(root/"db",public_key=pub.hex(),session_id="test-session",
                                        environment_id="test-environment",source_code_sha256=g.digest(b"fixture"))
            def signed(captured,delivered,tag):
                expected=verifier.issue(1)
                body={**expected,"session_id":"test-session","protocol":rp.PROTOCOL,"capture_id":tag,
                      "capture_index":1,"acquired_at_ns":time.time_ns(),"image_sha256":g.digest(captured),
                      "source_code_sha256":g.digest(b"fixture"),"key_id":g.digest(pub)}
                receipt={**body,"signature":key.sign(rp.canonical(body)).hex()}
                return g.Frame(delivered,tag,time.time(),receipt,expected)
            bad=signed(now,old,"replaced")
            self.assertEqual(verifier.check(bad.png,bad.receipt,expected=bad.expected).reason,"capture_bytes_replaced")
            self.assertEqual(verifier.check(now,bad.receipt,expected=bad.expected).reason,"capture_challenge_already_closed")
            seen=[]; acted=[]
            class Checker:
                def decide(self,raw):
                    seen.append(raw)
                    return g.Decision("YES",g.digest(raw),"review-call","test-revision","test-contract")
            gate=g.ImageGate(Checker(),receipt_guard=verifier,revision="test-revision",contract_sha256="test-contract",
                             journal=g.Journal(root/"journal"),recapture_seconds=0)
            frames=iter([signed(now,old,"transport-change"),signed(now,now,"fresh")])
            result=g.GateController(gate).step(g.Frame(None,"absent",0),lambda:next(frames),
                         lambda f:acted.append(f.png) or "WAIT",lambda text:text,lambda _:{"dispatched":True},
                         cancelled=lambda:False)
            self.assertEqual(result["status"],"dispatched")
            self.assertEqual((seen,acted),([now],[now]))
            self.assertEqual((gate.precheck_no,gate.receipt_no,gate.recaptures),(1,1,2))

    def test_identical_pixels_alone_do_not_prove_boundary(self):
        frame=g.Frame.captured(png("red")); act={"type":"scroll","direction":"down"}
        state={"kind":"boundary","scroll_top":50,"client_height":50,"scroll_height":100,
               "scroll_width":40,"client_width":40,"events":[]}
        audit={"before":state,"after":dict(state),"receipt":{"action_sequence":1}}
        self.assertFalse(tc.certified_boundary(frame,frame,act,audit))
        audit["after"]["events"]=[{"kind":"wheel","trusted":True,"delta_y":1}]
        self.assertTrue(tc.certified_boundary(frame,frame,act,audit))

    def test_recorded_denominators(self):
        b,d=benchmark(),defense()
        self.assertEqual(round(b["all"]["flags_pct"],1),46.3)
        self.assertEqual(round(d["full/all/on"]["usable_same_decision_forward_pct"],1),94.1)
        self.assertEqual(d["full/all/on"]["bad_forward_pct"],0)
        t=d["temporal"]
        self.assertEqual((t["recovered_among_confirmed_pct"],t["confirmed_recovery_among_assigned_pct"]), (90,75))
        self.assertEqual(t["false_first_hold_on_usable_controls_pct"],6.25)
