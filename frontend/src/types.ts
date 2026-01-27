export type League = 'nba' | 'ncaa';

export interface TeamStats {
    pointsPerGame: number;
    reboundsPerGame: number;
    assistsPerGame: number;
    fieldGoalPct: number;
    threePointPct: number;
    freeThrowPct: number;
    netRating: number;
}

export interface GameFactor {
    label: string;
    value: number; // 0-100
    impact: 'positive' | 'negative' | 'neutral';
}

export const LEAGUES = [
    { id: "nba", name: "NBA", fullName: "National Basketball Association" },
    { id: "ncaa", name: "NCAA", fullName: "College Basketball" },
];

export interface Prediction {
    id: string;
    league: League;
    awayTeam: {
        name: string;
        code: string;
        logo: string;
        record: string;
        stats: TeamStats;
    };
    homeTeam: {
        name: string;
        code: string;
        logo: string;
        record: string;
        stats: TeamStats;
    };
    marketTotal: number;
    modelTotal: number;
    edge: number;
    confidence: 'lock' | 'strong' | 'lean';
    time: string;
    date: string;
    trace: string[];
    factors: GameFactor[];
    forecastData: {
        time: string;
        awayVal: number;
        homeVal: number;
    }[];
}

export interface PlayerProp {
    id: string;
    name: string;
    team: string;
    teamCode: string;
    position: string;
    image: string;
    propType: 'PTS' | 'REB' | 'AST' | 'P+R+A';
    line: number;
    projection: number;
    edge: number;
    edgePct: number;
    usageBoost: boolean;
    recentTrend: number[]; // Last 5 games
}

export interface InjuryEntry {
    id: string;
    player: string;
    team: string;
    teamCode: string;
    status: 'OUT' | 'DOUBTFUL' | 'QUESTIONABLE' | 'GTD';
    description: string;
    impactScore: number; // -10 to +10
    date: string;
}

export interface PerformanceMetric {
    league: League | 'TOTAL';
    record: string;
    roi: number;
    profit: number;
    winPct: number;
    trend: number[];
}

// Player comparison types for VS layout
export interface PlayerAdvancedStats {
    astRatio: number;
    rebPct: number;
    efgPct: number;
    tsPct: number;
    usgPct: number;
    orebPct: number;
    drebPct: number;
}

export interface Player {
    id: string;
    name: string;
    team: string;
    teamCode: string;
    teamLogo: string;
    number: number;
    position: string;
    image: string;
    height: string;
    weight: string;
    experience: string;
    // Basic stats
    ppg: number;
    rpg: number;
    apg: number;
    pie: number; // Player Impact Estimate
    netRating: number;
    // Advanced stats
    advancedStats: PlayerAdvancedStats;
}

export interface PlayerComparison {
    id: string;
    player1: Player;
    player2: Player;
    // Comparison categories for horizontal bars
    comparisonBars: {
        label: string;
        labelShort: string;
        player1Value: number;
        player2Value: number;
        player1Pct: number;
        player2Pct: number;
    }[];
    // Forecast data for charts
    forecastData: {
        time: string;
        player1Val: number;
        player2Val: number;
    }[];
}

// Scoreboard game for carousel
export interface ScoreboardGame {
    id: string;
    league: League;
    awayTeam: {
        code: string;
        name: string;
        logo: string;
        score?: number;
    };
    homeTeam: {
        code: string;
        name: string;
        logo: string;
        score?: number;
    };
    status: 'scheduled' | 'live' | 'final';
    time: string;
    edge?: number;
}
