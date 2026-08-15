/**
 * Cloudflare Pages 로 옮겼을 때 쓰는 문지기.
 *
 * 사이트의 모든 요청이 여기를 먼저 지나간다. 아이디·비밀번호가 맞아야 통과한다.
 * 브라우저가 기본 제공하는 로그인 창(HTTP Basic 인증)을 쓴다.
 *
 * 비밀번호는 이 파일에 적지 않는다. Cloudflare 대시보드의
 * 설정 → 환경 변수(Environment variables) 에 넣는다. 그래야 저장소에 남지 않는다.
 *
 *   SITE_USER   로그인 아이디
 *   SITE_PASS   로그인 비밀번호  (영문·숫자로 만들 것. 한글은 인증 규격상 깨진다)
 *
 * GitHub Pages 에서는 이 파일이 아무 일도 하지 않는다. Cloudflare 에서만 작동한다.
 */

const REALM = 'WEVAPE SNS';

function ask(message) {
  return new Response(message, {
    status: 401,
    headers: {
      'WWW-Authenticate': `Basic realm="${REALM}", charset="UTF-8"`,
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'no-store',
    },
  });
}

export async function onRequest(context) {
  const { request, env, next } = context;
  const user = env.SITE_USER;
  const pass = env.SITE_PASS;

  // 환경 변수를 아직 안 넣었으면 아예 열지 않는다.
  // 실수로 잠금이 풀린 채 공개되는 것보다 안 열리는 쪽이 낫다.
  if (!user || !pass) {
    return new Response(
      '아직 설정이 끝나지 않았습니다.\n' +
      'Cloudflare 대시보드 → 설정 → 환경 변수에서 SITE_USER 와 SITE_PASS 를 넣어주세요.',
      { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }

  const header = request.headers.get('Authorization') || '';
  if (!header.startsWith('Basic ')) {
    return ask('로그인이 필요합니다.');
  }

  let decoded;
  try {
    decoded = atob(header.slice(6));
  } catch (e) {
    return ask('로그인 정보를 읽지 못했습니다.');
  }

  const i = decoded.indexOf(':');
  if (i < 0) return ask('로그인이 필요합니다.');

  if (decoded.slice(0, i) === user && decoded.slice(i + 1) === pass) {
    return next();                       // 통과 — 원래 페이지를 보여준다
  }
  return ask('아이디 또는 비밀번호가 맞지 않습니다.');
}
