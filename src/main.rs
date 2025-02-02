use anyhow::Context as _;
use poise::{
    serenity_prelude::{ClientBuilder, GatewayIntents},
    CreateReply,
};
use serenity::all::{CreateEmbed, CreateEmbedFooter};
use shuttle_runtime::SecretStore;
use shuttle_serenity::ShuttleSerenity;
use sqlx::Row;

struct Data {
    owner_id: u64,
    pool: sqlx::PgPool,
} // User data, which is stored and accessible in all command invocations
type Error = Box<dyn std::error::Error + Send + Sync>;
type Context<'a> = poise::Context<'a, Data, Error>;

/// Reports a question for not having enough information to solve.
#[poise::command(prefix_command, slash_command)]
async fn report(ctx: Context<'_>, question_id: i32, reason: Option<String>) -> Result<(), Error> {
    let pool = &ctx.data().pool;
    sqlx::query("INSERT INTO reports (question_id, reason) VALUES ($1, $2)")
        .bind(question_id)
        .bind(reason.unwrap_or_default())
        .execute(pool)
        .await?;

    ctx.say("Question reported. Thank you for your feedback!")
        .await?;

    Ok(())
}

/// Asks a question with the given course
#[poise::command(prefix_command, slash_command)]
async fn ask(ctx: Context<'_>, course: String) -> Result<(), Error> {
    let pool = &ctx.data().pool;

    let course = sqlx::query(
        "SELECT * FROM courses WHERE LOWER($1) = ANY (SELECT LOWER(unnest(tags))) OR LOWER($1) = LOWER(name)",
    )
    .bind(&course)
    .fetch_one(pool)
    .await;

    let course = match course {
        Ok(course) => course,
        Err(sqlx::Error::RowNotFound) => {
            ctx.say("Course not found. Use /courses to see available courses.")
                .await?;
            return Ok(());
        }
        Err(e) => return Err(e.into()),
    };

    let course_id = course.try_get::<i32, _>("id")?;

    let question =
        sqlx::query("SELECT * FROM questions WHERE subject_id = $1 ORDER BY RANDOM() LIMIT 1")
            .bind(course_id)
            .fetch_one(pool)
            .await?;

    let embed = CreateEmbed::default()
        .title("Question")
        .field(
            "Question",
            format!(
                "{}\n{}",
                question.try_get::<String, _>("question")?,
                question.try_get::<String, _>("answer_choices")?
            ),
            false,
        )
        .field(
            "Answers",
            format!(
                "||{}\n{}||",
                question.try_get::<String, _>("correct_answer")?,
                question.try_get::<String, _>("explanation")?
            ),
            false,
        )
        .footer(CreateEmbedFooter::new(format!(
            "ID: {}",
            question.try_get::<i32, _>("id")?
        )))
        .color(0x007848);

    // let message = format!(
    //     "**Question #{}**: {}\n{}\nAnswer: ||{}\n{}||",
    //     question.try_get::<i32, _>("id")?,
    //     question.try_get::<String, _>("question")?,
    //     question.try_get::<String, _>("answer_choices")?,
    //     question.try_get::<String, _>("correct_answer")?,
    //     question.try_get::<String, _>("explanation")?
    // );

    ctx.send(CreateReply::default().embed(embed)).await?;

    Ok(())
}

/// List available courses
#[poise::command(prefix_command, slash_command)]
async fn courses(ctx: Context<'_>) -> Result<(), Error> {
    let pool = &ctx.data().pool;

    let courses = sqlx::query("SELECT * FROM courses").fetch_all(pool).await?;

    let mut counts =
        sqlx::query("SELECT subject_id, COUNT(*) AS count FROM questions GROUP BY subject_id;")
            .fetch_all(pool)
            .await?
            .into_iter()
            .map(|row| {
                let id: i32 = row.get("subject_id");
                let count: i64 = row.get("count");
                (id, count)
            });

    let mut message = String::new();
    if courses.is_empty() {
        ctx.say("No courses found").await?;
        return Ok(());
    }

    for course in courses {
        let tags = course.try_get::<Vec<String>, _>("tags")?.join(", ");
        let id = course.try_get::<i32, _>("id")?;
        message.push_str(&format!(
            "{}: {} [{}] - {} questions\n",
            course.try_get::<String, _>("name")?,
            id,
            tags,
            counts
                .find_map(|e| if e.0 == id { Some(e.1) } else { None })
                .unwrap_or_default()
        ));
    }

    ctx.say(format!("```{}```", message)).await?;

    Ok(())
}

#[poise::command(prefix_command, hide_in_help)]
async fn register(ctx: Context<'_>) -> Result<(), Error> {
    if ctx.author().id != ctx.data().owner_id {
        // silently continue
        return Ok(());
    }
    poise::builtins::register_application_commands_buttons(ctx).await?;
    Ok(())
}

/// Show this menu
#[poise::command(prefix_command, slash_command)]
async fn help(
    ctx: Context<'_>,
    #[description = "Specific command to show help about"] command: Option<String>,
) -> Result<(), Error> {
    let config = poise::builtins::HelpConfiguration {
        extra_text_at_bottom: "Type /help command for more info on a command.",
        ..Default::default()
    };
    poise::builtins::help(ctx, command.as_deref(), config).await?;
    Ok(())
}

#[shuttle_runtime::main]
async fn main(
    #[shuttle_runtime::Secrets] secret_store: SecretStore,
    #[shuttle_shared_db::Postgres(
        local_uri = "postgres://postgres:{secrets.POSTGRES_PASSWORD}@localhost:5432/postgres"
    )]
    pool: sqlx::PgPool,
) -> ShuttleSerenity {
    // Get the discord token set in `Secrets.toml`
    let discord_token = secret_store
        .get("DISCORD_TOKEN")
        .context("'DISCORD_TOKEN' was not found")?;
    let owner_id = secret_store
        .get("OWNER_ID")
        .context("'OWNER_ID' was not found")?
        .parse::<u64>()
        .context("Invalid 'OWNER_ID'")?;

    // migrate db
    sqlx::migrate!()
        .run(&pool)
        .await
        .expect("Failed to migrate database");

    let framework = poise::Framework::builder()
        .options(poise::FrameworkOptions {
            prefix_options: poise::PrefixFrameworkOptions {
                prefix: Some("!".into()),
                ..Default::default()
            },
            commands: vec![courses(), help(), register(), ask(), report()],
            ..Default::default()
        })
        .setup(move |_ctx, _ready, _framework| {
            Box::pin(async move {
                // poise::builtins::register_in_guild(
                //     ctx,
                //     &framework.options().commands,
                //     GuildId::new(756990368582729738),
                // )
                // .await
                // .expect("failed to register");
                Ok(Data { owner_id, pool })
            })
        })
        .build();

    let client = ClientBuilder::new(
        discord_token,
        GatewayIntents::non_privileged() | GatewayIntents::MESSAGE_CONTENT,
    )
    .framework(framework)
    .await
    .map_err(shuttle_runtime::CustomError::new)?;

    Ok(client.into())
}
