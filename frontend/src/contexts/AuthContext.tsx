/**
 * AuthContext.tsx
 *
 * React Contextを使ってアプリ全体で認証状態を共有するためのファイルです。
 *
 * 【設計の考え方（Cookie方式）】
 * - アクセストークン（短命30分）はReactのstateのみで管理します。
 *   → XSS攻撃でメモリが読まれることはないため安全です。
 *   → localStorageには保存しません（XSS攻撃で読まれる恐れがあるため）。
 *
 * - リフレッシュトークン（長命7日）はバックエンドが HttpOnly Cookie で管理します。
 *   → JavaScriptからCookieの値は読めないのでXSS攻撃で漏れません。
 *   → ブラウザが自動的にCookieを送受信するため、フロントエンドで管理する必要がありません。
 *
 * - アプリ起動時（ページリロード時）はリフレッシュAPIを呼び出してセッションを復元します。
 *   → CookieがあればバックエンドがRTを検証して新しいアクセストークンを返します。
 *   → Cookieがなければ（未ログインまたは期限切れ）401が返りログアウト状態になります。
 */

import {
  createContext,
  useContext,
  useReducer,
  useEffect,
  type ReactNode,
} from "react";
import {
  loginApi,
  registerApi,
  logoutApi,
  refreshTokenApi,
  getMeApi,
} from "../api/auth";

// ─────────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────────

/**
 * ログイン中のユーザー情報
 * バックエンドのUserモデルから必要な情報だけを持ちます。
 */
interface User {
  /** ユーザーのID */
  id: number;
  /** ユーザーのメールアドレス */
  email: string;
}

/**
 * 認証状態の型定義
 * アプリ全体で共有される認証に関するすべての状態を表します。
 */
interface AuthState {
  /** ログイン中のユーザー情報。未ログインの場合はnull */
  user: User | null;
  /** APIリクエストに使うアクセストークン。未ログインの場合はnull（メモリのみで管理） */
  accessToken: string | null;
  /** アプリ起動時の認証チェック中かどうかを表すフラグ */
  isLoading: boolean;
}

/**
 * useReducerで使うActionの型定義
 * どのような状態変化が起きるかをすべて列挙しています。
 */
type AuthAction =
  | {
      /** ログイン・登録成功時のアクション */
      type: "LOGIN_SUCCESS";
      payload: {
        user: User;
        accessToken: string;
      };
    }
  | {
      /** ログアウト時のアクション */
      type: "LOGOUT";
    }
  | {
      /** ローディング状態を切り替えるアクション */
      type: "SET_LOADING";
      payload: boolean;
    }
  | {
      /** アクセストークンを更新するアクション */
      type: "REFRESH_TOKEN";
      payload: {
        accessToken: string;
      };
    };

/**
 * AuthContextが提供する値の型
 * コンポーネントからuseAuth()で取得できる情報と操作をまとめています。
 */
interface AuthContextValue {
  /** 現在の認証状態（user, accessToken, isLoading） */
  state: AuthState;
  /**
   * ログインを実行します。
   * @param email - メールアドレス
   * @param password - パスワード
   */
  login: (email: string, password: string) => Promise<void>;
  /**
   * 新規登録を実行します。
   * @param email - メールアドレス
   * @param password - パスワード
   */
  register: (email: string, password: string) => Promise<void>;
  /** ログアウトを実行します。 */
  logout: () => Promise<void>;
  /** Cookieのリフレッシュトークンでアクセストークンを更新します。 */
  refreshToken: () => Promise<void>;
}

// ─────────────────────────────────────────────
// 初期状態
// ─────────────────────────────────────────────

/** 認証状態の初期値 */
const initialState: AuthState = {
  user: null,
  accessToken: null,
  // アプリ起動時は認証チェック中なのでtrueにしておく
  isLoading: true,
};

// ─────────────────────────────────────────────
// Reducer（状態を変更するロジック）
// ─────────────────────────────────────────────

/**
 * 認証状態を更新するreducer関数です。
 * actionの種類に応じて新しいstateを返します。
 *
 * 【reducerとは？】
 * 「現在の状態」と「何が起きたか（action）」を受け取り、
 * 「次の状態」を返す純粋関数です。
 * リフレッシュトークンはCookieで管理しているため、reducerでは操作しません。
 *
 * @param state - 現在の認証状態
 * @param action - 発生したアクション
 * @returns 新しい認証状態
 */
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "LOGIN_SUCCESS":
      // ログイン・登録成功：ユーザー情報とアクセストークンをstateにセット
      // リフレッシュトークンはバックエンドがHttpOnly Cookieで管理するため、ここでは操作しない
      return {
        ...state,
        user: action.payload.user,
        accessToken: action.payload.accessToken,
        isLoading: false,
      };

    case "LOGOUT":
      // ログアウト：stateの認証情報をクリア
      // Cookie の削除はバックエンドが行う（logout APIが Set-Cookie: Max-Age=0 を返す）
      return {
        ...state,
        user: null,
        accessToken: null,
        isLoading: false,
      };

    case "SET_LOADING":
      // ローディング状態を変更する
      return {
        ...state,
        isLoading: action.payload,
      };

    case "REFRESH_TOKEN":
      // アクセストークンだけを新しいものに更新する
      // 新しいリフレッシュトークンはバックエンドがCookieで自動更新する
      return {
        ...state,
        accessToken: action.payload.accessToken,
      };

    default:
      // 未知のアクション型の場合は現在の状態をそのまま返す
      return state;
  }
}

// ─────────────────────────────────────────────
// Context の作成
// ─────────────────────────────────────────────

/**
 * 認証コンテキスト
 * undefined を初期値とし、Provider の外で使われた場合にエラーにします。
 */
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ─────────────────────────────────────────────
// Provider コンポーネント
// ─────────────────────────────────────────────

/**
 * 認証状態をアプリ全体に提供するProviderコンポーネントです。
 * main.tsx で <App /> を囲むように配置してください。
 *
 * @param props.children - 子コンポーネント（アプリ全体）
 *
 * @example
 * // main.tsx での使い方
 * <AuthProvider>
 *   <App />
 * </AuthProvider>
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  // useReducerで認証状態を管理する
  // dispatch関数を使ってactionをreducerに送ることで状態を更新します
  const [state, dispatch] = useReducer(authReducer, initialState);

  // ─────────────────────────────────────────────
  // アプリ起動時の自動ログイン復元
  // ─────────────────────────────────────────────

  useEffect(() => {
    /**
     * ページリロード時にCookieのリフレッシュトークンを使ってセッションを復元します。
     *
     * CookieはJavaScriptから読めないため、存在確認はできません。
     * そのため無条件にリフレッシュAPIを呼び出し、
     * 成功すればログイン状態に、失敗すれば未ログイン状態にします。
     */
    async function restoreSession() {
      try {
        // リフレッシュAPIを呼ぶ（credentials: 'include' でCookieが自動送信される）
        // CookieにリフレッシュトークンがあればバックエンドがRTを検証してアクセストークンを返す
        const tokens = await refreshTokenApi();
        // 取得したアクセストークンでユーザー情報を取得
        const me = await getMeApi(tokens.access_token);

        // ログイン成功状態にセット
        dispatch({
          type: "LOGIN_SUCCESS",
          payload: {
            user: { id: me.id, email: me.email },
            accessToken: tokens.access_token,
          },
        });
      } catch {
        // Cookieがない・期限切れ・無効の場合は401が返ってここに来る
        // 未ログイン状態にセットする（エラーをユーザーには表示しない）
        dispatch({ type: "SET_LOADING", payload: false });
      }
    }

    // コンポーネントのマウント時に1回だけ実行する
    restoreSession();
  }, []); // 空配列 = マウント時のみ実行

  // ─────────────────────────────────────────────
  // 認証操作の関数
  // ─────────────────────────────────────────────

  /**
   * ログインを実行する関数です。
   * フォームの送信ボタンなどから呼び出してください。
   *
   * @param email - メールアドレス
   * @param password - パスワード
   * @throws {Error} ログイン失敗時（メールアドレス・パスワード不一致など）
   */
  async function login(email: string, password: string): Promise<void> {
    // APIでログイン（レスポンスでアクセストークン、Cookieでリフレッシュトークンを受け取る）
    const tokens = await loginApi(email, password);
    // 取得したアクセストークンでユーザー情報を取得
    const me = await getMeApi(tokens.access_token);

    dispatch({
      type: "LOGIN_SUCCESS",
      payload: {
        user: { id: me.id, email: me.email },
        accessToken: tokens.access_token,
      },
    });
  }

  /**
   * 新規ユーザー登録を実行する関数です。
   *
   * @param email - 登録するメールアドレス
   * @param password - 設定するパスワード
   * @throws {Error} 登録失敗時（メールアドレス重複など）
   */
  async function register(email: string, password: string): Promise<void> {
    // APIで登録（登録後すぐにログイン状態になる）
    const tokens = await registerApi(email, password);
    // 登録後すぐにログイン状態にするためユーザー情報を取得
    const me = await getMeApi(tokens.access_token);

    dispatch({
      type: "LOGIN_SUCCESS",
      payload: {
        user: { id: me.id, email: me.email },
        accessToken: tokens.access_token,
      },
    });
  }

  /**
   * ログアウトを実行する関数です。
   * バックエンドでリフレッシュトークンをDB失効させ、Cookieを削除します。
   */
  async function logout(): Promise<void> {
    if (state.accessToken) {
      try {
        // バックエンドでリフレッシュトークンをDB失効・Cookie削除する
        await logoutApi(state.accessToken);
      } catch {
        // APIエラーが起きても、クライアント側はログアウト状態にする
        // （バックエンドのトークン無効化が失敗してもUXを損なわないようにする）
      }
    }

    // クライアント側の状態をクリア
    dispatch({ type: "LOGOUT" });
  }

  /**
   * アクセストークンをリフレッシュする関数です。
   * CookieのリフレッシュトークンはブラウザがAPIへ自動送信します。
   *
   * @throws {Error} リフレッシュトークンが無効な場合（ログアウト状態になります）
   */
  async function refreshToken(): Promise<void> {
    try {
      // CookieのRTをブラウザが自動送信するのでパラメーター不要
      const tokens = await refreshTokenApi();
      dispatch({
        type: "REFRESH_TOKEN",
        payload: { accessToken: tokens.access_token },
      });
    } catch {
      // リフレッシュ失敗時はログアウト状態にする
      dispatch({ type: "LOGOUT" });
    }
  }

  // ─────────────────────────────────────────────
  // Contextに渡す値をまとめる
  // ─────────────────────────────────────────────

  /** コンテキストに公開する値 */
  const contextValue: AuthContextValue = {
    state,
    login,
    register,
    logout,
    refreshToken,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// ─────────────────────────────────────────────
// カスタムフック
// ─────────────────────────────────────────────

/**
 * 認証コンテキストを取得するカスタムフックです。
 * AuthProviderの配下のコンポーネントからのみ呼び出せます。
 *
 * @returns 認証状態と操作関数（state, login, register, logout, refreshToken）
 * @throws {Error} AuthProviderの外で呼び出した場合
 *
 * @example
 * // コンポーネント内での使い方
 * const { state, login, logout } = useAuth();
 * if (state.user) {
 *   console.log(`ようこそ、${state.user.email}さん`);
 * }
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    // AuthProviderの外でuseAuthを使おうとした場合はエラーにする
    throw new Error("useAuth は AuthProvider の内側で使用してください");
  }
  return context;
}

// AuthContextもexportする（型チェックや高度な使い方のため）
export { AuthContext };
