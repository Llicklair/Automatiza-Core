import { request } from "./client";

export interface SocialAccount {
    id: string;
    platform: string;
    account_id: string;
    account_name: string | null;
    is_active: boolean;
    created_at: string;
}

export interface Campaign {
    id: string;
    name: string;
    description: string | null;
    start_date: string | null;
    end_date: string | null;
    is_active: boolean;
}

export interface ScheduledPost {
    id: string;
    platform: string;
    content: string;
    image_url: string | null;
    scheduled_at: string | null;
    published_at: string | null;
    status: "draft" | "scheduled" | "published" | "failed";
    platform_post_id: string | null;
    error_message: string | null;
    social_account_id: string;
    campaign_id: string | null;
    created_at: string;
}

export interface CreatePostInput {
    social_account_id: string;
    platform: string;
    content: string;
    image_url?: string;
    campaign_id?: string;
    scheduled_at?: string;
}

export interface UpdatePostInput {
    content?: string;
    image_url?: string;
    scheduled_at?: string;
}

export interface GeneratePlanResponse {
    summary: string;
    post_ids: string[];
}

export interface PostMetric {
    post_id: string;
    platform: string;
    status: string;
    metric_date: string | null;
    impressions: number;
    reach: number;
    likes: number;
    comments: number;
    shares: number;
    clicks: number;
}

export interface CampaignMetrics {
    campaign_id: string;
    num_posts: number;
    totals: {
        impressions: number;
        reach: number;
        likes: number;
        comments: number;
        shares: number;
        clicks: number;
    };
    posts: PostMetric[];
}

export interface PublishBatchResponse {
    published: string[];
    failed: string[];
}

export interface ZernioConfig {
    id: string;
    label: string | null;
    default_profile_id: string | null;
    num_accounts: number;
}

export const marketingApi = {
    accounts: {
        list: () => request<SocialAccount[]>("/api/v1/marketing/accounts"),
        connect: (platform: string, providerConfigId?: string) =>
            request<{ auth_url: string }>(
                `/api/v1/marketing/accounts/connect/${platform}${providerConfigId ? `?provider_config_id=${providerConfigId}` : ""}`,
                { method: "POST" }
            ),
        disconnect: (id: string) =>
            request<void>(`/api/v1/marketing/accounts/${id}`, { method: "DELETE" }),
    },
    campaigns: {
        list: () => request<Campaign[]>("/api/v1/marketing/campaigns"),
        create: (data: { name: string; description?: string }) =>
            request<Campaign>("/api/v1/marketing/campaigns", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        metrics: (id: string) =>
            request<CampaignMetrics>(`/api/v1/marketing/campaigns/${id}/metrics`),
    },
    posts: {
        list: (params?: { status?: string }) =>
            request<ScheduledPost[]>(
                `/api/v1/marketing/posts${params?.status ? `?status=${params.status}` : ""}`
            ),
        create: (data: CreatePostInput) =>
            request<ScheduledPost>("/api/v1/marketing/posts", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        delete: (id: string) =>
            request<void>(`/api/v1/marketing/posts/${id}`, { method: "DELETE" }),
        update: (id: string, data: UpdatePostInput) =>
            request<ScheduledPost>(`/api/v1/marketing/posts/${id}`, {
                method: "PATCH",
                body: JSON.stringify(data),
            }),
        publish: (id: string) =>
            request<ScheduledPost>(`/api/v1/marketing/posts/${id}/publish`, { method: "POST" }),
        publishBatch: (postIds: string[]) =>
            request<PublishBatchResponse>("/api/v1/marketing/posts/publish-batch", {
                method: "POST",
                body: JSON.stringify({ post_ids: postIds }),
            }),
    },
    agent: {
        generatePlan: (prompt: string) =>
            request<GeneratePlanResponse>("/api/v1/marketing/agent/generate", {
                method: "POST",
                body: JSON.stringify({ prompt }),
            }),
        generateImage: (prompt: string) =>
            request<{ url: string }>("/api/v1/marketing/generate-image", {
                method: "POST",
                body: JSON.stringify({ prompt }),
            }),
    },
    zernioConfig: {
        list: () => request<ZernioConfig[]>("/api/v1/marketing/zernio-config"),
        add: (data: { api_key: string; label?: string }) =>
            request<ZernioConfig>("/api/v1/marketing/zernio-config", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        delete: (id: string) =>
            request<void>(`/api/v1/marketing/zernio-config/${id}`, { method: "DELETE" }),
    },
};
