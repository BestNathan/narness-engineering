use narness_workspace_example::{Priority, Route, route_task};

#[test]
fn public_routing_contract_is_stable() {
    let cases = [
        (Priority::Normal, false, Route::Queue),
        (Priority::Urgent, false, Route::FastLane),
        (Priority::Normal, true, Route::Blocked),
        (Priority::Urgent, true, Route::Blocked),
    ];

    for (priority, has_blocker, expected) in cases {
        assert_eq!(route_task(priority, has_blocker), expected);
    }
}
