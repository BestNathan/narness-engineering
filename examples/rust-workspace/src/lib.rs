#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Priority {
    Normal,
    Urgent,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Route {
    Queue,
    FastLane,
    Blocked,
}

pub fn route_task(priority: Priority, has_blocker: bool) -> Route {
    if has_blocker {
        return Route::Blocked;
    }

    match priority {
        Priority::Normal => Route::Queue,
        Priority::Urgent => Route::FastLane,
    }
}

#[cfg(test)]
mod tests {
    use super::{Priority, Route, route_task};

    #[test]
    fn blocker_always_wins() {
        assert_eq!(route_task(Priority::Normal, true), Route::Blocked);
        assert_eq!(route_task(Priority::Urgent, true), Route::Blocked);
    }

    #[test]
    fn normal_tasks_use_the_queue() {
        assert_eq!(route_task(Priority::Normal, false), Route::Queue);
    }

    #[test]
    fn urgent_tasks_use_the_fast_lane() {
        assert_eq!(route_task(Priority::Urgent, false), Route::FastLane);
    }
}
