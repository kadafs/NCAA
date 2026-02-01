/**
 * API Client for NCAA/NBA Backend
 * 
 * Centralized API calls to the backend server
 */

// Backend API base URL - update if backend runs on different port
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://ncaa-api-w2ry.onrender.com';

export interface NCAAGame {
    game: {
        gameID: string;
        gameState: string;
        startDate: string;
        startTime: string;
        startTimeEpoch: number;
        finalMessage?: string;
        currentPeriod?: string;
        currentPeriodSecondsRemaining?: number;
        away: {
            names: {
                char6: string;
                short: string;
                seo: string;
                full: string;
            };
            score?: number;
            winner?: boolean;
        };
        home: {
            names: {
                char6: string;
                short: string;
                seo: string;
                full: string;
            };
            score?: number;
            winner?: boolean;
        };
    };
}

export interface ScoreboardResponse {
    games: NCAAGame[];
    sport?: string;
    division?: string;
}

/**
 * Fetch scoreboard data for a specific sport and date
 * @param sport - Sport type (e.g., 'basketball-men', 'basketball-women')
 * @param division - Division (e.g., 'd1', 'd2', 'd3')
 * @param date - Date in YYYY/MM/DD format
 */
export async function fetchScoreboard(
    sport: string,
    division: string,
    date: string
): Promise<ScoreboardResponse> {
    const url = `${API_BASE_URL}/scoreboard/${sport}/${division}/${date}`;

    try {
        const response = await fetch(url, {
            headers: {
                'Accept': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch scoreboard: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching scoreboard:', error);
        throw error;
    }
}

/**
 * Fetch NBA scoreboard data for a specific date using ESPN API
 * ESPN provides a reliable public API for NBA game data
 */
export async function fetchNBAScoreboard(date: Date): Promise<ScoreboardResponse> {
    // Format date as YYYYMMDD for ESPN API
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const dateStr = `${year}${month}${day}`;

    const url = `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=${dateStr}`;

    try {
        const response = await fetch(url, {
            headers: {
                'Accept': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch NBA scoreboard: ${response.statusText}`);
        }

        const data = await response.json();

        // Transform ESPN data to our format
        const games: NCAAGame[] = data.events?.map((event: any) => {
            const competition = event.competitions[0];
            const homeTeam = competition.competitors.find((c: any) => c.homeAway === 'home');
            const awayTeam = competition.competitors.find((c: any) => c.homeAway === 'away');

            // Determine game state
            let gameState = 'pre';
            if (event.status.type.completed) {
                gameState = 'final';
            } else if (event.status.type.state === 'in') {
                gameState = 'live';
            }

            return {
                game: {
                    gameID: event.id,
                    gameState: gameState,
                    startDate: event.date,
                    startTime: event.status.type.shortDetail || '',
                    startTimeEpoch: new Date(event.date).getTime(),
                    currentPeriod: event.status.type.detail || '',
                    away: {
                        names: {
                            char6: awayTeam.team.abbreviation,
                            short: awayTeam.team.abbreviation,
                            seo: awayTeam.team.slug,
                            full: awayTeam.team.displayName
                        },
                        score: parseInt(awayTeam.score) || undefined,
                        winner: awayTeam.winner
                    },
                    home: {
                        names: {
                            char6: homeTeam.team.abbreviation,
                            short: homeTeam.team.abbreviation,
                            seo: homeTeam.team.slug,
                            full: homeTeam.team.displayName
                        },
                        score: parseInt(homeTeam.score) || undefined,
                        winner: homeTeam.winner
                    }
                }
            };
        }) || [];

        return { games };
    } catch (error) {
        console.error('Error fetching NBA scoreboard:', error);
        throw error;
    }
}

/**
 * Format date to YYYY/MM/DD for API calls
 */
export function formatDateForAPI(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}/${month}/${day}`;
}

/**
 * Get current date in ET timezone
 */
export function getCurrentETDate(): Date {
    // Convert to ET timezone
    const etDate = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
    return etDate;
}
