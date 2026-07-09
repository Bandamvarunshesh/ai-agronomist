import { NavLink } from "react-router-dom";

export function FarmIntelligenceNav({
  farmId,
}: {
  farmId: string;
}) {
  return (
    <nav className="subnav">
      <NavLink
        className={({ isActive }) =>
          isActive ? "subnav-link subnav-link-active" : "subnav-link"
        }
        end
        to={`/app/farms/${farmId}`}
      >
        Overview
      </NavLink>
      <NavLink
        className={({ isActive }) =>
          isActive ? "subnav-link subnav-link-active" : "subnav-link"
        }
        to={`/app/farms/${farmId}/weather`}
      >
        Weather
      </NavLink>
      <NavLink
        className={({ isActive }) =>
          isActive ? "subnav-link subnav-link-active" : "subnav-link"
        }
        to={`/app/farms/${farmId}/stage-advisory`}
      >
        Crop stage
      </NavLink>
      <NavLink
        className={({ isActive }) =>
          isActive ? "subnav-link subnav-link-active" : "subnav-link"
        }
        to={`/app/farms/${farmId}/recommendations`}
      >
        Recommendations
      </NavLink>
      <NavLink
        className={({ isActive }) =>
          isActive ? "subnav-link subnav-link-active" : "subnav-link"
        }
        to={`/app/farms/${farmId}/timeline`}
      >
        Timeline
      </NavLink>
    </nav>
  );
}
