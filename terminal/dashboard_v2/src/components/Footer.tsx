import quantsLogo from "../assets/quants_dark.png";

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="mt-auto border-t border-white/10 bg-gradient-to-r from-white/[0.03] to-transparent">
      <div className="flex items-center justify-between px-6 py-4 text-xs">
        <div className="flex items-center gap-2.5">
          <img
            src={quantsLogo}
            alt=""
            className="h-5 w-auto object-contain opacity-70"
          />
          <div className="flex items-baseline gap-1.5 text-white/40">
            <span className="font-semibold text-white/60 tracking-tight">
              SharkLazer
            </span>
            <span className="text-white/20">·</span>
            <span>A CU Quants project</span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-white/30">
          <span className="hidden sm:inline tracking-wide">
            Built by the CU Quants team
          </span>
          <span className="text-white/15">·</span>
          <span>&copy; {year} CU Quants</span>
        </div>
      </div>
    </footer>
  );
}
