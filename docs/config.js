// 시청자가 자기 값으로 바꾸는 유일한 파일 (설계 5절)
//
// API_BASE      Render 서비스 주소 (예: "https://maemul-check-api.onrender.com"). 끝에 / 없이.
//               로컬에서는 "http://localhost:8000" (python -m server.app)
// KAKAO_JS_KEY  카카오 개발자 → 내 앱 → 앱 키 → JavaScript 키. 비워도 주소검색 팝업은 동작하고,
//               넣으면 주소를 직접 타이핑했을 때 도로명 → 지번 변환을 해준다.
//               공개 키라 레포에 올려도 되지만, 카카오 플랫폼 → Web → 사이트 도메인 제한을 반드시 걸 것.
window.MAEMUL_CONFIG = {
  API_BASE: "http://localhost:8000",
  KAKAO_JS_KEY: "",
};
