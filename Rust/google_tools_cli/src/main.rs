use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Duration;

use anyhow::{anyhow, Context, Result};
use chrono::{DateTime, Duration as ChronoDuration, Utc};
use clap::{Args, Parser, Subcommand};
use reqwest::multipart::{Form, Part};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::json;
use tokio::time::sleep;
use url::Url;

const GOOGLE_TOKEN_ENDPOINT: &str = "https://oauth2.googleapis.com/token";
const GOOGLE_DEVICE_CODE_ENDPOINT: &str = "https://oauth2.googleapis.com/device/code";

#[derive(Parser, Debug)]
#[command(name = "google-tools-cli")]
#[command(about = "Google API tools migrated from Python scripts", long_about = None)]
struct Cli {
    #[arg(long, default_value = "tokens/credentials.json")]
    credentials: PathBuf,

    #[arg(long, default_value = "tokens/rust_google_token.json")]
    token: PathBuf,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    Auth(AuthArgs),
    Calendar(CalendarArgs),
    Youtube(YoutubeArgs),
    Gmail(GmailArgs),
    Sheets(SheetsArgs),
    Drive(DriveArgs),
}

#[derive(Args, Debug)]
struct AuthArgs {
    #[arg(long = "scope", required = true)]
    scopes: Vec<String>,
}

#[derive(Args, Debug)]
struct CalendarArgs {
    #[command(subcommand)]
    command: CalendarCommands,
}

#[derive(Subcommand, Debug)]
enum CalendarCommands {
    AddEvent(CalendarAddEventArgs),
    AddEventsJson(CalendarAddEventsJsonArgs),
}

#[derive(Args, Debug)]
struct CalendarAddEventArgs {
    #[arg(long)]
    calendar_id: String,
    #[arg(long)]
    title: String,
    #[arg(long)]
    date: String,
    #[arg(long)]
    description: Option<String>,
}

#[derive(Args, Debug)]
struct CalendarAddEventsJsonArgs {
    #[arg(long)]
    calendar_id: String,
    #[arg(long)]
    file: PathBuf,
}

#[derive(Serialize, Deserialize, Debug)]
struct CalendarEventInput {
    title: String,
    date: String,
    description: Option<String>,
}

#[derive(Args, Debug)]
struct YoutubeArgs {
    #[command(subcommand)]
    command: YoutubeCommands,
}

#[derive(Subcommand, Debug)]
enum YoutubeCommands {
    ExportPlaylist(YoutubeExportPlaylistArgs),
    ImportPlaylist(YoutubeImportPlaylistArgs),
}

#[derive(Args, Debug)]
struct YoutubeExportPlaylistArgs {
    #[arg(long)]
    playlist_id: String,
    #[arg(long)]
    output_csv: PathBuf,
}

#[derive(Args, Debug)]
struct YoutubeImportPlaylistArgs {
    #[arg(long)]
    playlist_id: String,
    #[arg(long)]
    input_csv: PathBuf,
    #[arg(long, default_value = "URL")]
    url_column: String,
}

#[derive(Args, Debug)]
struct GmailArgs {
    #[command(subcommand)]
    command: GmailCommands,
}

#[derive(Subcommand, Debug)]
enum GmailCommands {
    ExportSearch(GmailExportArgs),
}

#[derive(Args, Debug)]
struct GmailExportArgs {
    #[arg(long)]
    query: String,
    #[arg(long)]
    output_csv: PathBuf,
    #[arg(long, default_value_t = 100)]
    max_results: u32,
}

#[derive(Args, Debug)]
struct SheetsArgs {
    #[command(subcommand)]
    command: SheetsCommands,
}

#[derive(Subcommand, Debug)]
enum SheetsCommands {
    AppendCsv(SheetsAppendCsvArgs),
}

#[derive(Args, Debug)]
struct SheetsAppendCsvArgs {
    #[arg(long)]
    spreadsheet_id: String,
    #[arg(long)]
    sheet_name: String,
    #[arg(long)]
    csv_path: PathBuf,
}

#[derive(Args, Debug)]
struct DriveArgs {
    #[command(subcommand)]
    command: DriveCommands,
}

#[derive(Subcommand, Debug)]
enum DriveCommands {
    UploadFile(DriveUploadFileArgs),
}

#[derive(Args, Debug)]
struct DriveUploadFileArgs {
    #[arg(long)]
    file_path: PathBuf,
    #[arg(long)]
    folder_id: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct StoredToken {
    access_token: String,
    refresh_token: Option<String>,
    expires_at: Option<DateTime<Utc>>,
    scopes: Vec<String>,
}

#[derive(Deserialize)]
struct DeviceCodeResponse {
    device_code: String,
    user_code: String,
    verification_url: Option<String>,
    verification_uri: Option<String>,
    verification_uri_complete: Option<String>,
    expires_in: i64,
    interval: Option<u64>,
}

#[derive(Deserialize)]
struct TokenResponse {
    access_token: String,
    token_type: String,
    expires_in: i64,
    refresh_token: Option<String>,
    scope: Option<String>,
}

#[derive(Deserialize)]
struct TokenErrorResponse {
    error: String,
}

#[derive(Deserialize)]
struct CredentialsRoot {
    installed: Option<OAuthClient>,
    web: Option<OAuthClient>,
}

#[derive(Deserialize)]
struct OAuthClient {
    client_id: String,
    client_secret: Option<String>,
}

#[derive(Clone)]
struct AuthContext {
    credentials_path: PathBuf,
    token_path: PathBuf,
    client: Client,
}

impl AuthContext {
    fn new(credentials_path: PathBuf, token_path: PathBuf) -> Self {
        Self {
            credentials_path,
            token_path,
            client: Client::new(),
        }
    }

    async fn ensure_access_token(&self, required_scopes: &[&str]) -> Result<String> {
        let required: Vec<String> = required_scopes.iter().map(|s| s.to_string()).collect();
        let mut token = self.load_token().ok();

        if let Some(existing) = token.as_ref() {
            if !scopes_contain_all(&existing.scopes, &required) {
                token = None;
            }
        }

        if let Some(existing) = token.as_ref() {
            if !is_expired(existing.expires_at) {
                return Ok(existing.access_token.clone());
            }
        }

        if let Some(existing) = token {
            if let Some(refresh_token) = existing.refresh_token.clone() {
                let refreshed = self
                    .refresh_access_token(&refresh_token, &required)
                    .await
                    .context("failed to refresh access token")?;
                self.save_token(&refreshed)?;
                return Ok(refreshed.access_token);
            }
        }

        let issued = self
            .run_device_flow(&required)
            .await
            .context("failed to complete device OAuth flow")?;
        self.save_token(&issued)?;
        Ok(issued.access_token)
    }

    fn load_client_credentials(&self) -> Result<(String, Option<String>)> {
        let raw = fs::read_to_string(&self.credentials_path).with_context(|| {
            format!(
                "failed to read credentials file: {}",
                self.credentials_path.display()
            )
        })?;

        let parsed: CredentialsRoot =
            serde_json::from_str(&raw).context("invalid credentials.json format")?;

        let client = parsed
            .installed
            .or(parsed.web)
            .ok_or_else(|| anyhow!("credentials.json must include installed or web OAuth client"))?;

        Ok((client.client_id, client.client_secret))
    }

    fn load_token(&self) -> Result<StoredToken> {
        let raw = fs::read_to_string(&self.token_path)
            .with_context(|| format!("failed to read token file: {}", self.token_path.display()))?;
        let token: StoredToken = serde_json::from_str(&raw).context("invalid token JSON")?;
        Ok(token)
    }

    fn save_token(&self, token: &StoredToken) -> Result<()> {
        if let Some(parent) = self.token_path.parent() {
            fs::create_dir_all(parent)
                .with_context(|| format!("failed to create directory: {}", parent.display()))?;
        }
        let json = serde_json::to_string_pretty(token)?;
        fs::write(&self.token_path, json)
            .with_context(|| format!("failed to write token file: {}", self.token_path.display()))?;
        Ok(())
    }

    async fn refresh_access_token(
        &self,
        refresh_token: &str,
        scopes: &[String],
    ) -> Result<StoredToken> {
        let (client_id, client_secret) = self.load_client_credentials()?;

        let mut form = vec![
            ("client_id", client_id),
            ("grant_type", "refresh_token".to_string()),
            ("refresh_token", refresh_token.to_string()),
        ];

        if let Some(secret) = client_secret {
            form.push(("client_secret", secret));
        }

        let res = self
            .client
            .post(GOOGLE_TOKEN_ENDPOINT)
            .form(&form)
            .send()
            .await?;

        if !res.status().is_success() {
            let body = res.text().await.unwrap_or_default();
            return Err(anyhow!("refresh token request failed: {}", body));
        }

        let token: TokenResponse = res.json().await?;
        let expires_at = Utc::now() + ChronoDuration::seconds(token.expires_in.max(0));

        Ok(StoredToken {
            access_token: token.access_token,
            refresh_token: Some(refresh_token.to_string()),
            expires_at: Some(expires_at),
            scopes: scopes.to_vec(),
        })
    }

    async fn run_device_flow(&self, scopes: &[String]) -> Result<StoredToken> {
        let (client_id, client_secret) = self.load_client_credentials()?;

        let scope_joined = scopes.join(" ");
        let device_code_response = self
            .client
            .post(GOOGLE_DEVICE_CODE_ENDPOINT)
            .form(&[("client_id", client_id.clone()), ("scope", scope_joined.clone())])
            .send()
            .await?;

        if !device_code_response.status().is_success() {
            let body = device_code_response.text().await.unwrap_or_default();
            return Err(anyhow!("device code request failed: {}", body));
        }

        let payload: DeviceCodeResponse = device_code_response.json().await?;
        let verify_url = payload
            .verification_uri_complete
            .clone()
            .or(payload.verification_url.clone())
            .or(payload.verification_uri.clone())
            .unwrap_or_else(|| "https://www.google.com/device".to_string());

        println!("[Auth] Open this URL and complete authentication:");
        println!("[Auth] {}", verify_url);
        println!("[Auth] User code: {}", payload.user_code);

        let interval = payload.interval.unwrap_or(5);
        let deadline = Utc::now() + ChronoDuration::seconds(payload.expires_in.max(0));

        loop {
            if Utc::now() > deadline {
                return Err(anyhow!("device authorization timed out"));
            }

            let mut form = vec![
                ("client_id", client_id.clone()),
                (
                    "grant_type",
                    "urn:ietf:params:oauth:grant-type:device_code".to_string(),
                ),
                ("device_code", payload.device_code.clone()),
            ];

            if let Some(secret) = client_secret.clone() {
                form.push(("client_secret", secret));
            }

            let poll = self.client.post(GOOGLE_TOKEN_ENDPOINT).form(&form).send().await?;

            if poll.status().is_success() {
                let token: TokenResponse = poll.json().await?;
                let expires_at = Utc::now() + ChronoDuration::seconds(token.expires_in.max(0));
                let token_scopes = token
                    .scope
                    .as_deref()
                    .map(|s| s.split(' ').map(|v| v.to_string()).collect())
                    .unwrap_or_else(|| scopes.to_vec());

                return Ok(StoredToken {
                    access_token: token.access_token,
                    refresh_token: token.refresh_token,
                    expires_at: Some(expires_at),
                    scopes: token_scopes,
                });
            }

            let error_payload = poll.json::<TokenErrorResponse>().await.unwrap_or(TokenErrorResponse {
                error: "unknown_error".to_string(),
            });

            match error_payload.error.as_str() {
                "authorization_pending" => {
                    sleep(Duration::from_secs(interval)).await;
                }
                "slow_down" => {
                    sleep(Duration::from_secs(interval + 5)).await;
                }
                other => {
                    return Err(anyhow!("device flow failed: {}", other));
                }
            }
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let auth = AuthContext::new(cli.credentials, cli.token);

    match cli.command {
        Commands::Auth(args) => {
            let scopes: Vec<&str> = args.scopes.iter().map(|s| s.as_str()).collect();
            let token = auth.ensure_access_token(&scopes).await?;
            println!("[Auth] Access token is ready (length={})", token.len());
        }
        Commands::Calendar(args) => match args.command {
            CalendarCommands::AddEvent(cmd) => {
                calendar_add_event(&auth, cmd).await?;
            }
            CalendarCommands::AddEventsJson(cmd) => {
                calendar_add_events_json(&auth, cmd).await?;
            }
        },
        Commands::Youtube(args) => match args.command {
            YoutubeCommands::ExportPlaylist(cmd) => youtube_export_playlist(&auth, cmd).await?,
            YoutubeCommands::ImportPlaylist(cmd) => youtube_import_playlist(&auth, cmd).await?,
        },
        Commands::Gmail(args) => match args.command {
            GmailCommands::ExportSearch(cmd) => gmail_export_search(&auth, cmd).await?,
        },
        Commands::Sheets(args) => match args.command {
            SheetsCommands::AppendCsv(cmd) => sheets_append_csv(&auth, cmd).await?,
        },
        Commands::Drive(args) => match args.command {
            DriveCommands::UploadFile(cmd) => drive_upload_file(&auth, cmd).await?,
        },
    }

    Ok(())
}

async fn calendar_add_event(auth: &AuthContext, args: CalendarAddEventArgs) -> Result<()> {
    let token = auth
        .ensure_access_token(&["https://www.googleapis.com/auth/calendar.events"])
        .await?;

    let payload = json!({
        "summary": args.title,
        "description": args.description.unwrap_or_default(),
        "start": { "date": args.date },
        "end": { "date": args.date },
    });

    let url = format!(
        "https://www.googleapis.com/calendar/v3/calendars/{}/events",
        urlencoding::encode(&args.calendar_id)
    );

    let res = auth
        .client
        .post(url)
        .bearer_auth(token)
        .json(&payload)
        .send()
        .await?;

    if !res.status().is_success() {
        return Err(anyhow!(
            "failed to add calendar event: {}",
            res.text().await.unwrap_or_default()
        ));
    }

    println!("[Calendar] Event added to {}", args.calendar_id);
    Ok(())
}

async fn calendar_add_events_json(auth: &AuthContext, args: CalendarAddEventsJsonArgs) -> Result<()> {
    let events_raw = fs::read_to_string(&args.file)
        .with_context(|| format!("failed to read file: {}", args.file.display()))?;
    let events: Vec<CalendarEventInput> = serde_json::from_str(&events_raw)
        .context("invalid JSON. expected array of {title, date, description?}")?;

    for event in events {
        calendar_add_event(
            auth,
            CalendarAddEventArgs {
                calendar_id: args.calendar_id.clone(),
                title: event.title,
                date: event.date,
                description: event.description,
            },
        )
        .await?;
    }

    Ok(())
}

async fn youtube_export_playlist(auth: &AuthContext, args: YoutubeExportPlaylistArgs) -> Result<()> {
    let token = auth
        .ensure_access_token(&["https://www.googleapis.com/auth/youtube.readonly"])
        .await?;

    let mut writer = csv::Writer::from_path(&args.output_csv)
        .with_context(|| format!("failed to open CSV: {}", args.output_csv.display()))?;
    writer.write_record(["タイトル", "URL"])?;

    let mut next_page_token: Option<String> = None;
    let mut total = 0usize;

    loop {
        let mut url = Url::parse("https://www.googleapis.com/youtube/v3/playlistItems")?;
        {
            let mut qp = url.query_pairs_mut();
            qp.append_pair("part", "snippet,contentDetails");
            qp.append_pair("maxResults", "50");
            qp.append_pair("playlistId", &args.playlist_id);
            if let Some(token) = next_page_token.as_deref() {
                qp.append_pair("pageToken", token);
            }
        }

        let res = auth.client.get(url).bearer_auth(&token).send().await?;
        if !res.status().is_success() {
            return Err(anyhow!(
                "failed to fetch playlist: {}",
                res.text().await.unwrap_or_default()
            ));
        }

        let body: serde_json::Value = res.json().await?;
        if let Some(items) = body.get("items").and_then(|v| v.as_array()) {
            for item in items {
                let title = item
                    .get("snippet")
                    .and_then(|s| s.get("title"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                let video_id = item
                    .get("contentDetails")
                    .and_then(|d| d.get("videoId"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();

                if !video_id.is_empty() {
                    writer.write_record([title, format!("https://www.youtube.com/watch?v={video_id}")])?;
                    total += 1;
                }
            }
        }

        next_page_token = body
            .get("nextPageToken")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());

        if next_page_token.is_none() {
            break;
        }
    }

    writer.flush()?;
    println!("[YouTube] Exported {} records -> {}", total, args.output_csv.display());
    Ok(())
}

async fn youtube_import_playlist(auth: &AuthContext, args: YoutubeImportPlaylistArgs) -> Result<()> {
    let token = auth
        .ensure_access_token(&["https://www.googleapis.com/auth/youtube"])
        .await?;

    let mut reader = csv::Reader::from_path(&args.input_csv)
        .with_context(|| format!("failed to open CSV: {}", args.input_csv.display()))?;

    let headers = reader.headers()?.clone();
    let idx = headers
        .iter()
        .position(|h| h == args.url_column)
        .ok_or_else(|| anyhow!("URL column '{}' not found", args.url_column))?;

    let mut inserted = 0usize;
    for row in reader.records() {
        let row = row?;
        let url_str = row.get(idx).unwrap_or("").trim();
        if url_str.is_empty() {
            continue;
        }

        let Some(video_id) = extract_youtube_video_id(url_str) else {
            println!("[YouTube][Warn] skipped invalid URL: {}", url_str);
            continue;
        };

        let payload = json!({
            "snippet": {
                "playlistId": args.playlist_id.clone(),
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        });

        let mut endpoint = Url::parse("https://www.googleapis.com/youtube/v3/playlistItems")?;
        endpoint.query_pairs_mut().append_pair("part", "snippet");

        let res = auth
            .client
            .post(endpoint)
            .bearer_auth(&token)
            .json(&payload)
            .send()
            .await?;

        if !res.status().is_success() {
            println!(
                "[YouTube][Warn] failed to insert {}: {}",
                video_id,
                res.text().await.unwrap_or_default()
            );
            continue;
        }

        inserted += 1;
    }

    println!("[YouTube] Imported {} videos", inserted);
    Ok(())
}

fn extract_youtube_video_id(url_str: &str) -> Option<String> {
    let parsed = Url::parse(url_str).ok()?;
    let host = parsed.host_str()?.to_lowercase();

    if host.contains("youtu.be") {
        return parsed
            .path_segments()
            .and_then(|mut seg| seg.next().map(|v| v.to_string()));
    }

    if host.contains("youtube.com") {
        if let Some(v) = parsed.query_pairs().find(|(k, _)| k == "v") {
            return Some(v.1.to_string());
        }

        let segments: Vec<&str> = parsed.path_segments()?.collect();
        if segments.len() >= 2 && (segments[0] == "shorts" || segments[0] == "embed") {
            return Some(segments[1].to_string());
        }
    }

    None
}

#[derive(Serialize)]
struct GmailCsvRow {
    id: String,
    thread_id: String,
    date: String,
    from: String,
    subject: String,
    snippet: String,
}

async fn gmail_export_search(auth: &AuthContext, args: GmailExportArgs) -> Result<()> {
    let token = auth
        .ensure_access_token(&["https://www.googleapis.com/auth/gmail.readonly"])
        .await?;

    let mut list_url = Url::parse("https://gmail.googleapis.com/gmail/v1/users/me/messages")?;
    {
        let mut qp = list_url.query_pairs_mut();
        qp.append_pair("q", &args.query);
        qp.append_pair("maxResults", &args.max_results.to_string());
    }

    let list_res = auth.client.get(list_url).bearer_auth(&token).send().await?;
    if !list_res.status().is_success() {
        return Err(anyhow!(
            "failed to list gmail messages: {}",
            list_res.text().await.unwrap_or_default()
        ));
    }

    let list_body: serde_json::Value = list_res.json().await?;
    let Some(messages) = list_body.get("messages").and_then(|v| v.as_array()) else {
        println!("[Gmail] no messages found");
        return Ok(());
    };

    let mut writer = csv::Writer::from_path(&args.output_csv)
        .with_context(|| format!("failed to open CSV: {}", args.output_csv.display()))?;
    writer.write_record(["id", "thread_id", "date", "from", "subject", "snippet"])?;

    for message in messages {
        let Some(message_id) = message.get("id").and_then(|v| v.as_str()) else {
            continue;
        };

        let mut msg_url = Url::parse(&format!(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
        ))?;
        {
            let mut qp = msg_url.query_pairs_mut();
            qp.append_pair("format", "metadata");
            qp.append_pair("metadataHeaders", "Subject");
            qp.append_pair("metadataHeaders", "Date");
            qp.append_pair("metadataHeaders", "From");
        }

        let msg_res = auth.client.get(msg_url).bearer_auth(&token).send().await?;
        if !msg_res.status().is_success() {
            println!(
                "[Gmail][Warn] failed to fetch message {}: {}",
                message_id,
                msg_res.text().await.unwrap_or_default()
            );
            continue;
        }

        let detail: serde_json::Value = msg_res.json().await?;
        let headers = detail
            .get("payload")
            .and_then(|p| p.get("headers"))
            .and_then(|h| h.as_array())
            .cloned()
            .unwrap_or_default();

        let header_value = |name: &str| -> String {
            headers
                .iter()
                .find_map(|h| {
                    let n = h.get("name")?.as_str()?;
                    if n.eq_ignore_ascii_case(name) {
                        h.get("value")?.as_str().map(|s| s.to_string())
                    } else {
                        None
                    }
                })
                .unwrap_or_default()
        };

        let row = GmailCsvRow {
            id: detail
                .get("id")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
            thread_id: detail
                .get("threadId")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
            date: header_value("Date"),
            from: header_value("From"),
            subject: header_value("Subject"),
            snippet: detail
                .get("snippet")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
        };

        writer.serialize(row)?;
    }

    writer.flush()?;
    println!("[Gmail] Export complete -> {}", args.output_csv.display());
    Ok(())
}

async fn sheets_append_csv(auth: &AuthContext, args: SheetsAppendCsvArgs) -> Result<()> {
    let token = auth
        .ensure_access_token(&["https://www.googleapis.com/auth/spreadsheets"])
        .await?;

    let mut reader = csv::Reader::from_path(&args.csv_path)
        .with_context(|| format!("failed to open CSV: {}", args.csv_path.display()))?;

    let mut rows: Vec<Vec<String>> = Vec::new();
    for record in reader.records() {
        let record = record?;
        rows.push(record.iter().map(|s| s.to_string()).collect());
    }

    if rows.is_empty() {
        return Err(anyhow!("CSV is empty: {}", args.csv_path.display()));
    }

    let range = format!("{}!A1", args.sheet_name);
    let endpoint = format!(
        "https://sheets.googleapis.com/v4/spreadsheets/{}/values/{}:append",
        args.spreadsheet_id,
        urlencoding::encode(&range)
    );

    let res = auth
        .client
        .post(endpoint)
        .bearer_auth(token)
        .query(&[("valueInputOption", "USER_ENTERED")])
        .json(&json!({
            "majorDimension": "ROWS",
            "values": rows,
        }))
        .send()
        .await?;

    if !res.status().is_success() {
        return Err(anyhow!(
            "failed to append sheets values: {}",
            res.text().await.unwrap_or_default()
        ));
    }

    println!(
        "[Sheets] Appended CSV to spreadsheet {} / sheet {}",
        args.spreadsheet_id, args.sheet_name
    );
    Ok(())
}

async fn drive_upload_file(auth: &AuthContext, args: DriveUploadFileArgs) -> Result<()> {
    let token = auth
        .ensure_access_token(&["https://www.googleapis.com/auth/drive.file"])
        .await?;

    let file_name = args
        .file_path
        .file_name()
        .and_then(|s| s.to_str())
        .ok_or_else(|| anyhow!("invalid file name: {}", args.file_path.display()))?
        .to_string();

    let file_bytes = fs::read(&args.file_path)
        .with_context(|| format!("failed to read file: {}", args.file_path.display()))?;
    let mime = mime_guess::from_path(&args.file_path)
        .first_or_octet_stream()
        .to_string();

    let metadata = if let Some(folder_id) = args.folder_id {
        json!({
            "name": file_name,
            "parents": [folder_id],
        })
    } else {
        json!({ "name": file_name })
    };

    let form = Form::new()
        .part(
            "metadata",
            Part::text(metadata.to_string()).mime_str("application/json; charset=UTF-8")?,
        )
        .part(
            "file",
            Part::bytes(file_bytes)
                .mime_str(&mime)?
                .file_name(file_name.clone()),
        );

    let res = auth
        .client
        .post("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart")
        .bearer_auth(token)
        .multipart(form)
        .send()
        .await?;

    if !res.status().is_success() {
        return Err(anyhow!(
            "failed to upload file to Drive: {}",
            res.text().await.unwrap_or_default()
        ));
    }

    let body: serde_json::Value = res.json().await?;
    let file_id = body.get("id").and_then(|v| v.as_str()).unwrap_or("unknown");
    println!("[Drive] Uploaded {} (id={})", file_name, file_id);
    Ok(())
}

fn scopes_contain_all(existing: &[String], required: &[String]) -> bool {
    let set: HashSet<&str> = existing.iter().map(String::as_str).collect();
    required.iter().all(|scope| set.contains(scope.as_str()))
}

fn is_expired(expires_at: Option<DateTime<Utc>>) -> bool {
    let Some(expiration) = expires_at else {
        return true;
    };
    expiration <= Utc::now() + ChronoDuration::seconds(30)
}

#[allow(dead_code)]
fn normalize_path(path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")).join(path)
    }
}
