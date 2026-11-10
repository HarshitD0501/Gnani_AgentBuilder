import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { getCallAnalytics } from '@/lib/analytics';
import { HELPDESK_COOKIE, helpDeskToken, tokenMatches } from '@/app/help-desk/auth';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(req: Request) {
  const expectedToken = helpDeskToken();

  // If operator gate token is configured, enforce authentication
  if (expectedToken) {
    const cookieStore = await cookies();
    const remembered = cookieStore.get(HELPDESK_COOKIE)?.value;
    const authHeader = req.headers.get('authorization')?.replace(/^Bearer\s+/i, '');
    const url = new URL(req.url);
    const queryToken = url.searchParams.get('token');

    const isAuthorized =
      tokenMatches(remembered, expectedToken) ||
      tokenMatches(authHeader || undefined, expectedToken) ||
      tokenMatches(queryToken || undefined, expectedToken);

    if (!isAuthorized) {
      return NextResponse.json(
        { error: 'Unauthorized: Operator authentication required' },
        { status: 401 }
      );
    }
  }

  // `dbPath` is dropped before the response leaves the server: this route is
  // sanitized, and the resolved path exposes the OS username and the
  // machine's directory layout. The dashboard never reads it.
  const { dbPath, ...analytics } = getCallAnalytics(50);

  if (analytics.error) {
    console.error(`[analytics] read failed for ${dbPath}: ${analytics.error}`);
  }

  return NextResponse.json(analytics);
}
