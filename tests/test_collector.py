import pytest
from unittest.mock import MagicMock, patch
from src.collector import parse_xml_response, fetch_sigungu_deals

MOCK_XML_SUCCESS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <dealAmount>   120,000 </dealAmount>
        <buildYear>2018</buildYear>
        <dealYear>2026</dealYear>
        <dealMonth>9</dealMonth>
        <dealDay>29</dealDay>
        <dong>역삼동</dong>
        <aptNm>역삼푸르지오</aptNm>
        <excluUseAr>84.9</excluUseAr>
        <floor>10</floor>
        <dealingGbn>중개거래</dealingGbn>
      </item>
    </items>
    <numOfRows>10</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>1</totalCount>
  </body>
</response>
"""

MOCK_XML_EMPTY = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items/>
    <numOfRows>10</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>0</totalCount>
  </body>
</response>
"""

def test_parse_xml_success():
    items = parse_xml_response(MOCK_XML_SUCCESS)
    assert len(items) == 1
    assert items[0]["aptNm"] == "역삼푸르지오"
    assert items[0]["dealDay"] == "29"
    assert items[0]["floor"] == "10"

def test_parse_xml_empty():
    items = parse_xml_response(MOCK_XML_EMPTY)
    assert items == []

def test_fetch_sigungu_deals_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = MOCK_XML_SUCCESS

    with patch("requests.get", return_value=mock_resp):
        items = fetch_sigungu_deals("11680", "202609", "fake_key", sido="서울특별시", sigungu="강남구")
        assert len(items) == 1
        assert items[0]["sido"] == "서울특별시"
        assert items[0]["sigungu"] == "강남구"
        assert items[0]["aptNm"] == "역삼푸르지오"

def test_fetch_sigungu_deals_network_error():
    with patch("requests.get", side_effect=Exception("Connection Timeout")):
        # 예외 발생 시 크래시 없이 빈 리스트를 반환하여 타 시군구 수집을 유지해야 함
        items = fetch_sigungu_deals("11680", "202609", "fake_key")
        assert items == []
