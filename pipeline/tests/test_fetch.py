import os
import types

from analog_finder import config
from analog_finder.fetch import common, earth, pds


def test_download_full_resume_and_skip(http_server, tmp_path):
    base, www, _ = http_server
    payload = os.urandom(300_000)
    (www / "file.img").write_bytes(payload)
    dest = tmp_path / "out" / "file.img"

    r = common.download(base + "file.img", dest, expected_bytes=len(payload), log=lambda s: None)
    assert r.status == "downloaded" and dest.read_bytes() == payload
    assert not dest.with_name("file.img.part").exists()

    r = common.download(base + "file.img", dest, expected_bytes=len(payload), log=lambda s: None)
    assert r.status == "present"

    # an interrupted download left a partial file: only the rest is fetched
    dest.unlink()
    dest.with_name("file.img.part").write_bytes(payload[:120_000])
    r = common.download(base + "file.img", dest, expected_bytes=len(payload), log=lambda s: None)
    assert r.status == "resumed" and dest.read_bytes() == payload

    # a short file under the final name is treated as partial, not as complete
    dest.write_bytes(payload[:50_000])
    r = common.download(base + "file.img", dest, expected_bytes=len(payload), log=lambda s: None)
    assert r.ok and dest.read_bytes() == payload


def test_download_when_server_ignores_range(http_server, tmp_path):
    base, www, handler = http_server
    handler.ignore_range = True
    payload = os.urandom(80_000)
    (www / "a.tab").write_bytes(payload)
    dest = tmp_path / "a.tab"
    dest.with_name("a.tab.part").write_bytes(b"garbage-from-an-older-run")
    r = common.download(base + "a.tab", dest, expected_bytes=len(payload), log=lambda s: None)
    assert r.ok and dest.read_bytes() == payload


def test_download_reports_missing_file_and_wrong_size(http_server, tmp_path):
    base, www, _ = http_server
    r = common.download(base + "nope.img", tmp_path / "nope.img", log=lambda s: None, retries=2)
    assert r.status == "failed" and "404" in r.message
    (www / "b.img").write_bytes(b"x" * 1000)
    r = common.download(base + "b.img", tmp_path / "b.img", expected_bytes=2000, retries=2,
                        backoff=0.01, log=lambda s: None)
    assert r.status == "failed"
    assert not (tmp_path / "b.img").exists()               # never leaves a wrong file under the final name


def test_fetch_datasets_and_check(http_server, project):
    base, www, _ = http_server
    (www / "one.img").write_bytes(b"a" * 4096)
    (www / "one.lbl").write_bytes(b"PDS_VERSION_ID = PDS3\r\nEND\r\n")
    ds = {"id": "t", "title": "test", "base_url": base, "dest": "data/raw/test",
          "files": [{"name": "one.img", "bytes": 4096, "label": "one.lbl"}]}
    assert [f["name"] for f in pds.planned_files(ds)] == ["one.img", "one.lbl"]
    dry = pds.fetch_datasets([ds], dry_run=True, log=lambda s: None)
    assert [r.status for r in dry] == ["planned", "planned"]
    assert not (project / "data" / "raw" / "test").exists()
    res = pds.fetch_datasets([ds], log=lambda s: None)
    assert all(r.ok for r in res)
    assert (project / "data" / "raw" / "test" / "one.img").stat().st_size == 4096
    assert (project / "data" / "raw" / "test" / "one.lbl").exists()


def test_manifest_matches_the_catalogue():
    """13 PDS data files, 1.60 GB, every data file has a label and a size."""
    pds_sets = [d for d in config.sources()["datasets"] if d.get("provider") == "pds"]
    files = [f for d in pds_sets for f in d["files"]]
    assert len(files) == 13
    assert pds.total_bytes(pds_sets) == 1_601_782_322
    assert all(f.get("bytes") and f.get("label") for f in files)
    assert all(d["base_url"].startswith("https://pds-geosciences.wustl.edu/") for d in pds_sets)
    names = {f["name"] for f in files}
    assert {"ldem_75s_240m.img", "dlre_prp_south.tab", "megt90n000gb.img", "h2o_sr_5x5.tab"} <= names
    # record sizes from the real labels: lines * samples * 2 bytes
    sizes = {f["name"]: f["bytes"] for f in files}
    assert sizes["ldem_75s_240m.img"] == 3812 * 3812 * 2
    assert sizes["megt90n000eb.img"] == 2880 * 5760 * 2
    assert sizes["megt90n000gb.img"] == 5760 * 11520 * 2
    assert sizes["dlre_prp_south.tab"] == (2_880_000 + 1) * 210
    ids = [d["id"] for d in config.sources()["datasets"]]
    assert len(ids) == len(set(ids))


def test_copdem_tile_names():
    assert earth.copdem_tile_name(75.38, -89.67) == "Copernicus_DSM_COG_30_N75_00_W090_00_DEM"
    assert earth.copdem_tile_name(-77.5, 162.5) == "Copernicus_DSM_COG_30_S78_00_E162_00_DEM"
    assert earth.copdem_tile_name(0.5, 0.5, arcsec=10) == "Copernicus_DSM_COG_10_N00_00_E000_00_DEM"
    assert earth.copdem_tile_name(-0.5, -0.5) == "Copernicus_DSM_COG_30_S01_00_W001_00_DEM"
    tiles = earth.copdem_tiles_around(75.38, -89.67, 0.5)
    assert (75, -90) in tiles and (74, -90) in tiles and len(tiles) >= 4


def test_power_request_and_annual_values(project):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"properties": {"parameter": {"T2M": {"JAN": -20.1, "ANN": -15.5}, "PRECTOTCORR": {"ANN": 0.3}}}}

    class FakeSession:
        def get(self, url, params=None, headers=None, timeout=None):
            calls.append((url, params))
            return FakeResponse()

    pts = [{"id": "haughton", "lat": 75.38, "lon": -89.67}]
    res = earth.fetch_power(pts, pause_s=0, log=lambda s: None, session=FakeSession())
    assert res[0].status == "downloaded"
    url, params = calls[0]
    assert url == "https://power.larc.nasa.gov/api/temporal/climatology/point"
    assert params["latitude"] == "75.3800" and params["longitude"] == "-89.6700" and params["format"] == "JSON"
    assert len(params["parameters"].split(",")) <= 20
    out = project / "data" / "raw" / "earth" / "power" / "haughton.json"
    assert earth.power_annual(out) == {"T2M": -15.5, "PRECTOTCORR": 0.3}
    assert earth.fetch_power(pts, pause_s=0, log=lambda s: None, session=FakeSession())[0].status == "present"


def test_earthdata_search_logic_with_a_fake_library(project):
    """Version fallback, yearly window and 'latest' selection, without touching the network."""
    log = []

    class Granule(dict):
        def size(self):
            return 10.0

    def granule(begin):
        return Granule(umm={"TemporalExtent": {"RangeDateTime": {"BeginningDateTime": begin}}})

    def search_data(short_name, version=None, temporal=None, **kw):
        log.append((short_name, version, temporal))
        if short_name == "MOD10CM" and version == "61":
            return []                                    # pretend the version string is wrong
        if short_name == "MCD12C1":
            return [granule("2021-01-01"), granule("2023-01-01"), granule("2022-01-01")]
        return [granule("2023-01-01")] * (12 if temporal else 1)

    downloaded = []
    fake = types.SimpleNamespace(
        login=lambda persist=True: types.SimpleNamespace(authenticated=True),
        search_data=search_data,
        download=lambda granules, path: downloaded.append((len(granules), path)) or ["f"] * len(granules))

    res = earth.fetch_earthdata(year=2023, log=lambda s: None, earthaccess=fake)
    assert all(r.ok for r in res) and len(res) == 7                  # 7 Earthdata products in the manifest
    assert ("MOD11C3", "061", ("2023-01-01", "2023-12-31")) in log
    assert ("MOD10CM", None, ("2023-01-01", "2023-12-31")) in log          # retried without the version
    by_path = {os.path.basename(p): n for n, p in downloaded}
    assert by_path["modis_lst"] == 12 and by_path["modis_lc"] == 1 and by_path["emit"] == 1

    dry = earth.fetch_earthdata(ids=["earth_mod11c3"], dry_run=True, log=lambda s: None, earthaccess=fake)
    assert [r.status for r in dry] == ["planned"]


def test_granule_size_in_any_earthaccess_version():
    class AsMethod(dict):
        def size(self):
            return 12.5

    class AsNumber(dict):
        size = 7.25                                    # newer earthaccess: a plain number

    class FromMetadata(dict):
        size = 0.0

    meta = {"umm": {"DataGranule": {"ArchiveAndDistributionInformation": [
        {"SizeInBytes": 2_000_000}, {"Size": 1.5, "SizeUnit": "MB"}, {"Size": 1, "SizeUnit": "GB"}]}}}
    assert earth._granule_mb(AsMethod()) == 12.5
    assert earth._granule_mb(AsNumber()) == 7.25
    assert earth._granule_mb(FromMetadata(meta)) == 2.0 + 1.5 + 1000.0
    assert earth._granule_mb(FromMetadata()) == 0.0
