import { NextResponse } from 'next/server';

export async function GET(
    request: Request,
    { params }: { params: Promise<{ school: string }> }
) {
    const { school } = await params;
    const { searchParams } = new URL(request.url);
    const dark = searchParams.get('dark');

    const bgParam = dark !== null && dark !== 'false' ? 'bgd' : 'bgl';
    // Standardize slug: remove .svg if present
    const slug = school.replace(/\.svg$/, '');

    const targetUrl = `https://www.ncaa.com/sites/default/files/images/logos/schools/${bgParam}/${slug}.svg`;

    try {
        const res = await fetch(targetUrl, {
            headers: {
                'User-Agent':
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.ncaa.com/',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            },
            // Vercel/Next.js specific cache control
            next: { revalidate: 604800 }, // Cache for a week
        });

        if (!res.ok) {
            return new NextResponse('Logo not found', { status: 404 });
        }

        const svgContent = await res.text();

        return new NextResponse(svgContent, {
            headers: {
                'Content-Type': 'image/svg+xml',
                'Cache-Control': 'public, max-age=604800, s-maxage=604800, stale-while-revalidate=86400',
            },
        });
    } catch (error) {
        console.error('Logo Proxy Error:', error);
        return new NextResponse('Internal Server Error', { status: 500 });
    }
}
