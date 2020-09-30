# Moderation action codes.
MOD_ACTIONS = list(range(9))
BUMP_POST, OPEN_POST, TOGGLE_ACCEPT, MOVE_ANSWER, DUPLICATE, OFFTOPIC, DELETE, CLOSE, REPORT_SPAM = MOD_ACTIONS

# Filter actions
RANK, VIEWS, REPLIES, TAGGED, VOTES, VISIT, REPUTATION, JOINED, ACTIVITY = ("rank", "views", "replies",
                                                          "tagged", "votes", "visit", "reputation",
                                                          "joined", "activity")
# Map to
ORDER_MAPPER = {
    RANK: "-rank",
    TAGGED: '-tagged',
    VIEWS: "-view_count",
    REPLIES: "-reply_count",
    VOTES: "-thread_votecount",
    VISIT: '-profile__last_login',
    REPUTATION: '-profile__score',
    JOINED: '-profile__date_joined',
    ACTIVITY: '-profile__date_joined'
}

MYVOTES_CACHE_KEY = "MYVOTES"
TAGS_CACHE_KEY = "TAGS"
MYPOSTS_CACHE_KEY = "MYPOSTS"
FOLLOWING_CACHE_KEY = "FOLLOWING"
BOOKMARKS_CACHE_KEY = "BOOKMARKS"
MYTAGS_CACHE_KEY = "MYTAGS"

SIMILAR_CACHE_KEY = "SIMILAR"
USERS_CACHE_KEY = "MENTIONED_USERS"

# The name of the session count data.
COUNT_DATA_KEY = "COUNT_DATA"

# Redirection field name.
REDIRECT_FIELD_NAME = 'next'

MYVOTES, MYPOSTS, MYTAGS, OPEN, FOLLOWING, SHOW_SPAM = ["myvotes", "myposts", "mytags", "open", "following", "spam"]

BOOKMARKS, MESSAGE = ["bookmarks", "message"]

MENTIONED, COMMUNITY, LATEST = ["mentioned", "community", "latest"]

# Post type names for filtering in the UI.
JOBS, TOOLS, TUTORIALS, FORUM, PLANET = ["jobs", "tools", "tutorials", "forum", "planet"]

# Topics that have a default tabs
TOPICS_WITH_TABS = [
    MYPOSTS, MYTAGS, FOLLOWING,
    BOOKMARKS, MYVOTES, MESSAGE, COMMUNITY, LATEST
]

PRIVATE_TOPICS = [MYPOSTS, MYTAGS, MESSAGE, MENTIONED,
                  BOOKMARKS, FOLLOWING, MYVOTES
                  ]
